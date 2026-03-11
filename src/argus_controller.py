"""
ARGUS – Headless Hardware Controller
======================================
Extracts hardware management logic from main.py into a standalone class
that operates without a GUI.  Used by web_server.py for the web-based
client-server mode.

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
"""

from __future__ import annotations

import collections
import logging
import logging.handlers
import threading
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Re-use helpers from main.py to avoid duplication
# ---------------------------------------------------------------------------
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    DEFAULT_CONFIG,
    HEALTH_CRITICAL,
    HEALTH_DEGRADED,
    HEALTH_HEALTHY,
    _deep_merge,
    load_config,
    save_config,
    normalize_azimuth,
)

# Hardware imports with graceful fallback ------------------------------------
try:
    from ascom_handler import ASCOMHandler
except ImportError:
    ASCOMHandler = None  # type: ignore[assignment,misc]

try:
    from serial_ctrl import SerialController
except ImportError:
    SerialController = None  # type: ignore[assignment,misc]

try:
    from vision import VisionSystem
except ImportError:
    VisionSystem = None  # type: ignore[assignment,misc]

try:
    from math_utils import MathUtils
except ImportError:
    MathUtils = None  # type: ignore[assignment,misc]

try:
    from dome_drivers import create_driver
except ImportError:
    create_driver = None  # type: ignore[assignment,misc]

try:
    from simulation_sensor import SimulationSensor
except ImportError:
    SimulationSensor = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ring-buffer log handler
# ---------------------------------------------------------------------------
class _RingBufferLogHandler(logging.Handler):
    """Logging handler that stores recent messages in a deque."""

    def __init__(self, buf: collections.deque):
        super().__init__()
        self._buf = buf

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._buf.append(self.format(record))
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# ArgusController – headless version
# ---------------------------------------------------------------------------
class ArgusController:
    """Headless hardware controller for ARGUS web-server mode.

    Manages hardware resources (ASCOM, serial, vision) and exposes a
    ``get_state()`` snapshot suitable for JSON serialisation and WebSocket
    push (~10 Hz).

    The control loop runs in a background daemon thread started by
    :meth:`start`.
    """

    _RECONNECT_INTERVAL: float = 10.0

    def __init__(self, config: Optional[dict] = None) -> None:
        if config is None:
            config = load_config()
        self.config = config

        # -- Log ring buffer ---------------------------------------------
        self._log_buf: collections.deque = collections.deque(maxlen=200)
        self._ring_handler = _RingBufferLogHandler(self._log_buf)
        self._ring_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(self._ring_handler)

        # -- Thread state ------------------------------------------------
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # -- Dome / mount state ------------------------------------------
        self._mode: str = "MANUAL"
        self._is_parked: bool = False
        self.is_slaved: bool = False

        # Mount telemetry (filled by ASCOM or simulation)
        self._mount_az: float = 180.0
        self._mount_alt: float = 45.0
        self._mount_ra: float = 0.0
        self._mount_dec: float = 0.0

        # Drift correction last value (degrees)
        self._drift_correction_deg: float = 0.0

        # Safety warning string or None
        self._safety_warning: Optional[str] = None

        # Health
        self._health: str = HEALTH_CRITICAL

        # Outlier rejection state
        self._last_drift_az: Optional[float] = None
        self._stable_drift_count: int = 0
        self._pending_drift_az: Optional[float] = None

        self._last_reconnect_time: float = 0.0
        self._last_vision_ok: bool = True

        # Vision marker state
        self._marker_found: bool = False

        # -- Hardware handles --------------------------------------------
        self.sensor = SimulationSensor() if SimulationSensor else None
        self.ascom = None
        self.serial = None
        self.vision: Optional[object] = None
        self.math_utils = None
        self.dome_driver = None

        self._init_hardware()

    # ------------------------------------------------------------------ #
    #  Hardware initialisation                                            #
    # ------------------------------------------------------------------ #
    def _init_hardware(self) -> None:
        self._init_math_utils()
        self._init_ascom()
        self._sync_site_data()
        self._init_serial()
        self._init_dome_driver()
        self._init_vision()

    def _init_math_utils(self) -> None:
        if MathUtils is None:
            return
        try:
            math_cfg = self.config.get("math", {})
            obs = math_cfg.get("observatory", {})
            dome = math_cfg.get("dome", {})
            mount_cfg = math_cfg.get("mount", {})
            self.math_utils = MathUtils(
                latitude=obs.get("latitude", 0.0),
                longitude=obs.get("longitude", 0.0),
                elevation=obs.get("elevation", 0),
                dome_radius=dome.get("radius", 2.5),
                pier_height=mount_cfg.get("pier_height", 1.5),
                gem_offset_east=mount_cfg.get("gem_offset_east", 0.0),
                gem_offset_north=mount_cfg.get("gem_offset_north", 0.0),
            )
        except Exception as exc:
            logger.error("Failed to initialize MathUtils: %s", exc)

    def _init_ascom(self) -> None:
        if ASCOMHandler is None:
            return
        try:
            ascom_cfg = self.config.get("ascom", {})
            prog_id = ascom_cfg.get("telescope_prog_id", "ASCOM.Simulator.Telescope")
            handler = ASCOMHandler(prog_id)
            if handler.connect():
                self.ascom = handler
            else:
                logger.warning("ASCOM connection failed – simulation mode")
        except Exception as exc:
            logger.error("Failed to initialize ASCOM: %s", exc)

    def _sync_site_data(self) -> None:
        if self.ascom is None:
            return
        try:
            site = self.ascom.get_site_data()
            if site is None:
                return
            obs = self.config.get("math", {}).get("observatory", {})
            changed = False
            for key in ("latitude", "longitude", "elevation"):
                mount_val = site.get(key, 0.0)
                cfg_val = obs.get(key, 0.0)
                if mount_val is not None and (cfg_val == 0.0 or abs(mount_val - cfg_val) > 1e-4):
                    obs[key] = mount_val
                    changed = True
            if changed:
                self.config.setdefault("math", {})["observatory"] = obs
                save_config(self.config)
        except Exception as exc:
            logger.warning("Could not sync site data: %s", exc)

    def _init_serial(self) -> None:
        if SerialController is None:
            return
        try:
            hw_cfg = self.config.get("hardware", {})
            ctrl = SerialController(
                port=hw_cfg.get("serial_port", "COM3"),
                baud_rate=hw_cfg.get("baud_rate", 9600),
                timeout=hw_cfg.get("timeout", 1.0),
            )
            if ctrl.connect():
                self.serial = ctrl
            else:
                logger.warning("Serial connection failed – simulation mode")
        except Exception as exc:
            logger.error("Failed to initialize SerialController: %s", exc)

    def _init_dome_driver(self) -> None:
        self.dome_driver = None
        if create_driver is None:
            return
        try:
            self.dome_driver = create_driver(self.config, self.serial)
        except Exception as exc:
            logger.error("Failed to initialize dome driver: %s", exc)

    def _init_vision(self) -> None:
        if VisionSystem is None:
            return
        try:
            vis_cfg = self.config.get("vision", {})
            res = vis_cfg.get("resolution", {})
            aruco_cfg = vis_cfg.get("aruco", {})
            cam = VisionSystem(
                camera_index=vis_cfg.get("camera_index", 0),
                resolution=(res.get("width", 1280), res.get("height", 720)),
                aruco_dict=aruco_cfg.get("dictionary", "DICT_4X4_50"),
                marker_size=aruco_cfg.get("marker_size", 0.05),
            )
            if cam.open_camera():
                self.vision = cam
            else:
                found = VisionSystem.find_working_camera()
                if found is not None:
                    cam2 = VisionSystem(
                        camera_index=found,
                        resolution=(res.get("width", 1280), res.get("height", 720)),
                        aruco_dict=aruco_cfg.get("dictionary", "DICT_4X4_50"),
                        marker_size=aruco_cfg.get("marker_size", 0.05),
                    )
                    if cam2.open_camera():
                        self.vision = cam2
                        self.config.setdefault("vision", {})["camera_index"] = found
                        save_config(self.config)
                else:
                    logger.warning("No working camera found – vision disabled")
        except Exception as exc:
            logger.error("Failed to initialize VisionSystem: %s", exc)

    # ------------------------------------------------------------------ #
    #  Properties                                                         #
    # ------------------------------------------------------------------ #
    @property
    def current_azimuth(self) -> float:
        """Current dome azimuth in degrees [0, 360)."""
        if self.dome_driver is not None:
            return self.dome_driver.position
        if self.sensor is not None:
            return self.sensor.get_azimuth()
        return 0.0

    @property
    def is_slewing(self) -> bool:
        if self.dome_driver is not None:
            return self.dome_driver.slewing
        if self.sensor is not None:
            return abs(self.sensor.slew_rate) > 1e-6
        return False

    @property
    def is_parked(self) -> bool:
        return self._is_parked

    @property
    def mode(self) -> str:
        with self._lock:
            return self._mode

    @property
    def hw_connected(self) -> bool:
        return self.serial is not None and getattr(self.serial, "connected", False)

    @property
    def ascom_connected(self) -> bool:
        return self.ascom is not None and getattr(self.ascom, "connected", False)

    @property
    def vision_active(self) -> bool:
        return self.vision is not None and getattr(self.vision, "camera_open", False)

    # ------------------------------------------------------------------ #
    #  Commands                                                           #
    # ------------------------------------------------------------------ #
    def move_dome(self, azimuth: float) -> None:
        """Slew dome to *azimuth* (degrees, 0–360)."""
        azimuth = normalize_azimuth(azimuth)
        dome_limits = self.config.get("dome", {})
        az_min = dome_limits.get("az_min", 0.0)
        az_max = dome_limits.get("az_max", 360.0)
        if az_min != 0.0 or az_max != 360.0:
            if az_min < az_max:
                azimuth = max(az_min, min(az_max, azimuth))
            else:
                if not (azimuth >= az_min or azimuth <= az_max):
                    dist_min = min(abs(azimuth - az_min),
                                   abs(azimuth - az_min - 360),
                                   abs(azimuth - az_min + 360))
                    dist_max = min(abs(azimuth - az_max),
                                   abs(azimuth - az_max - 360),
                                   abs(azimuth - az_max + 360))
                    azimuth = az_min if dist_min <= dist_max else az_max
        self._is_parked = False
        speed = self.config.get("control", {}).get("max_speed", 100)
        if self.dome_driver is not None:
            self.dome_driver.slew_to(azimuth, speed)
        elif self.serial:
            self.serial.move_to_azimuth(azimuth, speed)
        logger.info("Move dome to %.1f°", azimuth)

    def stop_dome(self) -> None:
        """Immediately stop dome movement."""
        if self.dome_driver is not None:
            self.dome_driver.abort()
        if self.serial:
            self.serial.stop_motor()
        if self.sensor:
            self.sensor.slew_rate = 0.0
        logger.info("Dome stopped")

    def park_dome(self) -> None:
        """Park dome at azimuth 0°."""
        self.move_dome(0.0)
        self._is_parked = True
        logger.info("Dome parking at 0°")

    def home_dome(self) -> None:
        """Run homing sequence using configuration parameters."""
        homing = self.config.get("hardware", {}).get("homing", {})
        if not homing.get("enabled", False):
            logger.warning("Homing is not enabled in configuration")
            return
        home_az = homing.get("azimuth", 0.0)
        direction = homing.get("direction", "CW")
        if self.dome_driver is not None:
            self.dome_driver.home(home_az, direction)
        logger.info("Homing complete – position set to %.1f°", home_az)

    def set_mode(self, mode: str) -> None:
        """Set operating mode: ``'MANUAL'`` or ``'AUTO'``."""
        with self._lock:
            self._mode = mode
        logger.info("Mode set to %s", mode)

    def set_slaved(self, slaved: bool) -> None:
        """Enable or disable slaving to the telescope."""
        self.is_slaved = slaved
        logger.info("Slaved set to %s", slaved)

    # ------------------------------------------------------------------ #
    #  State snapshot                                                     #
    # ------------------------------------------------------------------ #
    def get_state(self) -> dict:
        """Return a JSON-serialisable snapshot of the current state."""
        return {
            "dome_az": self.current_azimuth,
            "mount_az": self._mount_az,
            "mount_alt": self._mount_alt,
            "mount_ra": self._mount_ra,
            "mount_dec": self._mount_dec,
            "mode": self.mode,
            "is_slewing": self.is_slewing,
            "is_parked": self.is_parked,
            "is_slaved": self.is_slaved,
            "hardware_connected": self.hw_connected,
            "ascom_connected": self.ascom_connected,
            "vision_active": self.vision_active,
            "vision_marker_found": self._marker_found,
            "drift_correction": self._drift_correction_deg,
            "safety_warning": self._safety_warning,
            "log_messages": self.get_recent_logs(50),
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------------ #
    #  Logging helpers                                                    #
    # ------------------------------------------------------------------ #
    def get_recent_logs(self, n: int = 50) -> list:
        """Return the *n* most recent log messages."""
        buf = list(self._log_buf)
        return buf[-n:] if len(buf) > n else buf

    # ------------------------------------------------------------------ #
    #  Config update at runtime                                           #
    # ------------------------------------------------------------------ #
    def update_config(self, new_config: dict) -> None:
        """Merge *new_config* into the running configuration."""
        self.config = _deep_merge(self.config, new_config)
        logger.info("Configuration updated at runtime")

    # ------------------------------------------------------------------ #
    #  Control loop                                                       #
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Start the background control loop thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._control_loop, name="argus-ctrl", daemon=True
        )
        self._thread.start()
        logger.info("ArgusController control loop started")

    def stop_all(self) -> None:
        """Stop the control loop and release hardware resources."""
        self._running = False
        if self.dome_driver is not None:
            try:
                self.dome_driver.abort()
            except Exception:
                pass
        if self.serial and getattr(self.serial, "connected", False):
            try:
                self.serial.stop_motor()
            except Exception:
                pass
        if self.sensor:
            self.sensor.slew_rate = 0.0
        if self.ascom:
            try:
                self.ascom.disconnect()
            except Exception:
                pass
        if self.vision:
            try:
                self.vision.close_camera()
            except Exception:
                pass
        logger.info("ArgusController stopped")

    # -- Outlier rejection (copied from main.ArgusController) ------------
    def _filter_drift(self, drift_az: float) -> Optional[float]:
        glitch_threshold = 5.0
        stability_tolerance = 1.0
        required_stable_frames = 3

        if self._last_drift_az is None:
            self._last_drift_az = drift_az
            return drift_az

        delta = abs(drift_az - self._last_drift_az)
        if delta <= glitch_threshold:
            self._last_drift_az = drift_az
            self._pending_drift_az = None
            self._stable_drift_count = 0
            return drift_az

        if self._pending_drift_az is not None and abs(drift_az - self._pending_drift_az) < stability_tolerance:
            self._stable_drift_count += 1
        else:
            self._pending_drift_az = drift_az
            self._stable_drift_count = 1

        if self._stable_drift_count >= required_stable_frames:
            self._last_drift_az = drift_az
            self._pending_drift_az = None
            self._stable_drift_count = 0
            return drift_az

        return None

    def _check_system_health(self) -> str:
        ascom_ok = self.ascom_connected
        serial_ok = self.hw_connected
        vision_ok = self.vision_active
        if ascom_ok and serial_ok and vision_ok:
            return HEALTH_HEALTHY
        if ascom_ok and serial_ok:
            return HEALTH_DEGRADED
        return HEALTH_CRITICAL

    def _try_reconnect_hardware(self) -> None:
        if (self.ascom is None or not self.ascom_connected) and ASCOMHandler is not None:
            try:
                ascom_cfg = self.config.get("ascom", {})
                handler = ASCOMHandler(ascom_cfg.get("telescope_prog_id", "ASCOM.Simulator.Telescope"))
                if handler.connect():
                    self.ascom = handler
                    logger.info("ASCOM telescope reconnected")
            except Exception:
                pass

        if (self.serial is None or not self.hw_connected) and SerialController is not None:
            try:
                hw_cfg = self.config.get("hardware", {})
                ctrl = SerialController(
                    port=hw_cfg.get("serial_port", "COM3"),
                    baud_rate=hw_cfg.get("baud_rate", 9600),
                    timeout=hw_cfg.get("timeout", 1.0),
                )
                if ctrl.connect():
                    self.serial = ctrl
                    self._init_dome_driver()
                    logger.info("Serial motor controller reconnected")
            except Exception:
                pass

        if (self.vision is None or not self.vision_active) and VisionSystem is not None:
            try:
                vis_cfg = self.config.get("vision", {})
                res = vis_cfg.get("resolution", {})
                aruco_cfg = vis_cfg.get("aruco", {})
                cam = VisionSystem(
                    camera_index=vis_cfg.get("camera_index", 0),
                    resolution=(res.get("width", 1280), res.get("height", 720)),
                    aruco_dict=aruco_cfg.get("dictionary", "DICT_4X4_50"),
                    marker_size=aruco_cfg.get("marker_size", 0.05),
                )
                if cam.open_camera():
                    self.vision = cam
                    logger.info("Camera reconnected")
            except Exception:
                pass

    def _control_loop(self) -> None:
        ctrl_cfg = self.config.get("control", {})
        update_rate = ctrl_cfg.get("update_rate", 10)
        interval = 1.0 / max(update_rate, 1)
        correction_threshold = ctrl_cfg.get("correction_threshold", 0.5)
        max_speed = ctrl_cfg.get("max_speed", 100)
        proportional_gain = ctrl_cfg.get("proportional_gain", 2.0)
        drift_enabled = ctrl_cfg.get("drift_correction_enabled", True)

        last = time.time()

        while self._running:
            try:
                now = time.time()
                dt = now - last
                last = now

                current_mode = self.mode

                if now - self._last_reconnect_time >= self._RECONNECT_INTERVAL:
                    self._last_reconnect_time = now
                    self._try_reconnect_hardware()

                health = self._check_system_health()
                self._health = health

                if health == HEALTH_CRITICAL and current_mode == "AUTO-SLAVE":
                    if self.serial:
                        try:
                            self.serial.stop_motor()
                        except Exception:
                            pass
                    if self.sensor:
                        self.sensor.slew_rate = 0.0

                if current_mode == "AUTO-SLAVE" and health != HEALTH_CRITICAL:
                    telescope_data = None
                    if self.ascom:
                        try:
                            telescope_data = self.ascom.get_all_data()
                        except Exception:
                            pass

                    if telescope_data and self.math_utils:
                        self._mount_az = telescope_data.get("azimuth", self._mount_az)
                        self._mount_alt = telescope_data.get("altitude", self._mount_alt)
                        self._mount_ra = telescope_data.get("ra", self._mount_ra)
                        self._mount_dec = telescope_data.get("dec", self._mount_dec)

                        target_az = self.math_utils.calculate_required_azimuth(
                            ra=telescope_data["ra"],
                            dec=telescope_data["dec"],
                            side_of_pier=telescope_data.get("side_of_pier"),
                        )
                        target_az = normalize_azimuth(target_az)

                        if drift_enabled and self.vision and health == HEALTH_HEALTHY:
                            try:
                                frame = self.vision.capture_frame()
                                if frame is not None:
                                    markers = self.vision.detect_markers(frame)
                                    self._marker_found = bool(markers)
                                    if markers:
                                        shape = markers.get("frame_shape")
                                        expected = (
                                            (shape[1] / 2, shape[0] / 2)
                                            if shape
                                            else (self.vision.resolution[0] / 2,
                                                  self.vision.resolution[1] / 2)
                                        )
                                        drift = self.vision.calculate_drift(markers, expected)
                                        if drift:
                                            corrected = self.math_utils.apply_drift_correction(
                                                target_az, drift
                                            )
                                            corrected = normalize_azimuth(corrected)
                                            accepted = self._filter_drift(corrected)
                                            if accepted is not None:
                                                self._drift_correction_deg = accepted - target_az
                                                target_az = accepted
                            except Exception:
                                pass

                        dome_az = self.current_azimuth
                        error = abs(target_az - dome_az)
                        if error > 180:
                            error = 360 - error
                        if error > correction_threshold and self.serial:
                            speed = min(int(error * proportional_gain), max_speed)
                            self.serial.move_to_azimuth(target_az, speed)

                # Safety check
                safety_cfg = self.config.get("safety", {})
                if safety_cfg.get("telescope_protrudes", False):
                    if self._mount_alt < safety_cfg.get("safe_altitude", 90.0):
                        self._safety_warning = "Telescope below safe altitude – rotation restricted"
                    else:
                        self._safety_warning = None
                else:
                    self._safety_warning = None

                if self.sensor:
                    self.sensor.update(dt)

                sleep_time = max(0.0, interval - (time.time() - now))
                time.sleep(sleep_time)

            except Exception as exc:
                logger.error("Control loop error: %s", exc, exc_info=True)
                if self.sensor:
                    self.sensor.slew_rate = 0.0
                time.sleep(interval)
