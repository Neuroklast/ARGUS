"""
ARGUS - Advanced Rotation Guidance Using Sensors
Main Application Entry Point (Controller Pattern)

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Loads config.yaml, initializes hardware modules, and provides
a state-machine-driven control loop for MANUAL and AUTO-SLAVE modes.
Includes degraded-mode logic, outlier rejection, hysteresis, and
production-grade rotating log files.
"""

import atexit
import logging
import logging.handlers
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import yaml
import flet as ft

from gui import ArgusGUI, COLOR_BG
from settings_gui import show_settings_dialog
from simulation_sensor import SimulationSensor
from localization import t, set_language

# Hardware imports with graceful fallback --------------------------------
try:
    from ascom_handler import ASCOMHandler
except ImportError:                     # pragma: no cover
    ASCOMHandler = None                 # type: ignore[assignment,misc]

try:
    from serial_ctrl import SerialController
except ImportError:                     # pragma: no cover
    SerialController = None             # type: ignore[assignment,misc]

try:
    from vision import VisionSystem
except ImportError:                     # pragma: no cover
    VisionSystem = None                 # type: ignore[assignment,misc]

try:
    from math_utils import MathUtils
except ImportError:                     # pragma: no cover
    MathUtils = None                    # type: ignore[assignment,misc]

try:
    from voice import VoiceAssistant
except ImportError:                     # pragma: no cover
    VoiceAssistant = None               # type: ignore[assignment,misc]

try:
    from calibration import OffsetSolver
except ImportError:                     # pragma: no cover
    OffsetSolver = None                 # type: ignore[assignment,misc]

try:
    from dome_drivers import create_driver, DomeDriver
except ImportError:                     # pragma: no cover
    create_driver = None                # type: ignore[assignment,misc]
    DomeDriver = None                   # type: ignore[assignment,misc]

try:
    from alpaca_server import AlpacaDomeServer
except ImportError:                     # pragma: no cover
    AlpacaDomeServer = None             # type: ignore[assignment,misc]

try:
    from data_loader import load_calibration_data
except ImportError:                     # pragma: no cover
    load_calibration_data = None        # type: ignore[assignment,misc]

try:
    from replay_handler import ReplayASCOMHandler
except ImportError:                     # pragma: no cover
    ReplayASCOMHandler = None           # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

from path_utils import get_base_path, resolve_path

DEFAULT_CONFIG_PATH = resolve_path("config.yaml")


# ---------------------------------------------------------------------------
# GUI Logging Handler – forwards log records to the GUI log terminal
# ---------------------------------------------------------------------------
class GuiLogHandler(logging.Handler):
    """Custom logging handler that forwards messages to the GUI log terminal.

    Calls the GUI's ``write_log()`` method directly. Since Flet handles
    thread-safe updates via ``page.update()`` inside ``write_log()``,
    no ``app.after()`` scheduling is needed.
    """

    def __init__(self, gui):
        super().__init__()
        self._gui = gui

    def emit(self, record):
        """Format *record* and append it to the GUI log terminal."""
        try:
            msg = self.format(record)
            self._gui.write_log(msg)
        except Exception:
            self.handleError(record)

# ---------------------------------------------------------------------------
# Default configuration – used as fallback when keys are missing / invalid
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: dict = {
    "language": "en",
    "ascom": {
        "telescope_prog_id": "ASCOM.Simulator.Telescope",
        "poll_interval": 1.0,
    },
    "vision": {
        "camera_index": 0,
        "resolution": {"width": 1280, "height": 720},
        "fps": 30,
        "aruco": {"dictionary": "DICT_4X4_50", "marker_size": 0.05},
    },
    "hardware": {
        "serial_port": "COM3",
        "baud_rate": 9600,
        "timeout": 1.0,
        "motor_type": "stepper",
        "protocol": "argus",
        "steps_per_degree": 100.0,
        "ticks_per_degree": 50.0,
        "degrees_per_second": 5.0,
        "encoder_tolerance": 0.5,
        "homing": {
            "enabled": False,
            "azimuth": 0.0,
            "direction": "CW",
        },
    },
    "math": {
        "observatory": {"latitude": 51.5074, "longitude": -0.1278, "elevation": 0},
        "dome": {"radius": 2.5, "slit_width": 0.8},
        "mount": {
            "pier_height": 1.5,
            "gem_offset_east": 0.0,
            "gem_offset_north": 0.0,
        },
    },
    "control": {
        "update_rate": 10,
        "drift_correction_enabled": True,
        "correction_threshold": 0.5,
        "max_speed": 100,
    },
    "logging": {
        "level": "INFO",
        "file": "argus.log",
        "console": True,
    },
    "safety": {
        "telescope_protrudes": True,
        "safe_altitude": 90.0,
        "max_nudge_while_protruding": 2.0,
    },
}

# Health-state constants
HEALTH_HEALTHY = "HEALTHY"
HEALTH_DEGRADED = "DEGRADED"
HEALTH_CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def _deep_merge(defaults: dict, overrides: dict) -> dict:
    """Recursively merge *overrides* into *defaults* (non-destructive)."""
    merged = dict(defaults)
    for key, default_val in defaults.items():
        if key not in overrides:
            logger.warning("Config key '%s' missing, using default %r", key, default_val)
            continue
        override_val = overrides[key]
        if isinstance(default_val, dict) and isinstance(override_val, dict):
            merged[key] = _deep_merge(default_val, override_val)
        elif isinstance(default_val, dict) and not isinstance(override_val, dict):
            logger.warning(
                "Config key '%s' has wrong type (expected dict), using default", key
            )
        elif not _type_ok(default_val, override_val):
            logger.warning(
                "Config key '%s' has wrong type (expected %s, got %s), using default %r",
                key,
                type(default_val).__name__,
                type(override_val).__name__,
                default_val,
            )
        else:
            merged[key] = override_val
    # Carry forward extra keys from overrides that are not in defaults
    for key in overrides:
        if key not in defaults:
            merged[key] = overrides[key]
    return merged


def _type_ok(default, value) -> bool:
    """Return True when *value* is type-compatible with *default*."""
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, (int, float))
    if isinstance(default, float):
        return isinstance(value, (int, float))
    if isinstance(default, str):
        return isinstance(value, str)
    return True  # unknown types pass through


def load_config(path: Optional[str] = None) -> dict:
    """Load configuration from a YAML file with validation.

    Missing keys or wrong types fall back to ``DEFAULT_CONFIG``.
    If the file cannot be parsed at all the full defaults are returned.

    Args:
        path: Path to config file.  Defaults to ``config.yaml`` in the
              repository root.

    Returns:
        Validated configuration dictionary.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        with open(config_path, "r") as fh:
            raw = yaml.safe_load(fh)
        if not isinstance(raw, dict):
            logger.warning("Config file did not produce a dict – using defaults")
            return dict(DEFAULT_CONFIG)
        logger.info("Configuration loaded from %s", config_path)
        return _deep_merge(DEFAULT_CONFIG, raw)
    except FileNotFoundError:
        logger.warning("Config file not found: %s – using defaults", config_path)
        return dict(DEFAULT_CONFIG)
    except yaml.YAMLError as exc:
        logger.error("Error parsing config file: %s – using defaults", exc)
        return dict(DEFAULT_CONFIG)


def save_config(config: dict, path: Optional[str] = None) -> None:
    """Write the configuration dictionary back to a YAML file.

    Uses ``yaml.dump`` with ``default_flow_style=False`` for a clean,
    human-readable output.

    Args:
        config: Configuration dictionary to persist.
        path:   Destination file.  Defaults to ``config.yaml`` in the
                repository root.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        with open(config_path, "w") as fh:
            yaml.dump(config, fh, default_flow_style=False, sort_keys=False)
        logger.info("Configuration saved to %s", config_path)
    except Exception as exc:
        logger.error("Failed to save configuration: %s", exc)


# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------
def normalize_azimuth(az: float) -> float:
    """Return *az* normalised to 0-360."""
    return az % 360.0


# ---------------------------------------------------------------------------
# Main controller
# ---------------------------------------------------------------------------
class ArgusController:
    """Controller that bridges the GUI and hardware modules.

    Supports **MANUAL** and **AUTO-SLAVE** modes with graceful
    degradation when hardware components are unavailable.
    """

    def __init__(self, config: Optional[dict] = None, gui: Optional['ArgusGUI'] = None):
        """Initialise the controller, hardware modules, and background loop.

        Args:
            config: Validated configuration dictionary.  When ``None``,
                    the default ``config.yaml`` is loaded automatically.
            gui:    Optional :class:`ArgusGUI` instance.  Pass ``None``
                    for headless / test operation.
        """
        if config is None:
            config = load_config()
        self.config = config

        self._setup_logging()

        # -- State machine -----------------------------------------------
        self._mode: str = "MANUAL"
        self._lock = threading.Lock()
        self._running = True
        self._last_status: str = "Stopped"
        self._last_vision_ok: bool = True
        self._health: str = HEALTH_HEALTHY
        self._last_reconnect_time: float = 0.0

        # -- Alpaca / slaving state --------------------------------------
        self.is_slaved: bool = False
        self._is_parked: bool = False

        # -- Outlier rejection state -------------------------------------
        self._last_drift_az: Optional[float] = None
        self._stable_drift_count: int = 0
        self._pending_drift_az: Optional[float] = None

        # -- GUI ----------------------------------------------------------
        self.gui = gui
        # Backward-compatible alias (used by some tests)
        self.app = gui

        if gui is not None:
            # -- Register GUI log handler --------------------------------
            gui_handler = GuiLogHandler(gui)
            gui_handler.setLevel(logging.INFO)
            gui_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
            logging.getLogger().addHandler(gui_handler)

        # Simulation fallback (always available)
        self.sensor = SimulationSensor()

        # Simulation mode state (virtual telescope position)
        self._sim_mount_az: float = 180.0
        self._sim_mount_alt: float = 45.0
        self._sim_slit_open: bool = False

        # Hardware handles (``None`` = unavailable)
        self.ascom = None
        self.serial = None
        self.vision = None
        self.math_utils = None

        self._init_math_utils()
        self._auto_setup_ascom()
        self._init_ascom()
        self._sync_site_data()
        self._init_serial()
        self._init_dome_driver()
        self._init_vision()
        self._init_voice()

        # -- Bind GUI callbacks ------------------------------------------
        if gui is not None:
            gui.btn_ccw.on_click = lambda e: self.on_move_left()
            gui.btn_stop.on_click = lambda e: self.on_stop()
            gui.btn_cw.on_click = lambda e: self.on_move_right()
            gui.mode_selector.on_change = lambda e: self.on_mode_changed(
                next(iter(e.control.selected), "MANUAL")
            )
            gui.btn_settings.on_click = lambda e: show_settings_dialog(
                gui.page, self.config, self._on_settings_saved,
            )
            gui.btn_diagnostics.on_click = lambda e: self._run_diagnostics()

            # Simulation controls
            gui.sim_az_slider.on_change = lambda e: self._on_sim_az_changed(
                e.control.value
            )
            gui.sim_alt_slider.on_change = lambda e: self._on_sim_alt_changed(
                e.control.value
            )
            gui.btn_sim_slit.on_click = lambda e: self._on_sim_slit_toggle()

        self._update_indicators()

        # -- Failsafe: register emergency stop on exit/crash ---------------
        self._register_failsafes()

        # -- Background control loop -------------------------------------
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()

    # ---- Logging --------------------------------------------------------
    def _setup_logging(self):
        """Configure the root logger with RotatingFileHandler."""
        log_cfg = self.config.get("logging", {})
        level = getattr(logging, log_cfg.get("level", "INFO"), logging.INFO)
        log_file = log_cfg.get("file")
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

        handlers: list = []
        if log_cfg.get("console", True):
            handlers.append(logging.StreamHandler())
        if log_file:
            rotating = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,   # 5 MB
                backupCount=5,
            )
            handlers.append(rotating)

        logging.basicConfig(
            level=level,
            format=fmt,
            handlers=handlers or [logging.StreamHandler()],
        )

    # ---- Failsafe mechanisms -------------------------------------------
    def _register_failsafes(self):
        """Register emergency-stop handlers for process exit and signals.

        Ensures motors are stopped immediately when:
        * The Python process exits (atexit)
        * An unhandled exception reaches the top level
        * A termination signal (SIGTERM/SIGINT) is received
        """
        atexit.register(self._emergency_stop)

        self._orig_excepthook = sys.excepthook
        sys.excepthook = self._crash_handler

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, self._signal_handler)
            except (OSError, ValueError):
                pass  # Cannot set signal handler from non-main thread

    def _emergency_stop(self):
        """Unconditionally stop all motors – used as a last-resort failsafe."""
        self._running = False
        try:
            if self.dome_driver is not None:
                self.dome_driver.abort()
        except Exception:
            pass
        try:
            if self.serial is not None and self.serial.connected:
                self.serial.stop_motor()
        except Exception:
            pass
        self.sensor.slew_rate = 0.0

    def _crash_handler(self, exc_type, exc_value, exc_tb):
        """Global exception hook: stop motors, then call the original hook."""
        logger.critical("Unhandled exception – EMERGENCY STOP", exc_info=(exc_type, exc_value, exc_tb))
        self._emergency_stop()
        if self._orig_excepthook:
            self._orig_excepthook(exc_type, exc_value, exc_tb)

    def _signal_handler(self, signum, frame):
        """Handle SIGTERM/SIGINT: stop motors and shut down cleanly."""
        logger.warning("Signal %s received – EMERGENCY STOP", signum)
        self._emergency_stop()
        self.shutdown()

    # ---- Hardware initialisation helpers --------------------------------
    def _init_math_utils(self):
        """Create the :class:`MathUtils` instance from observatory config."""
        if MathUtils is None:
            logger.warning("MathUtils module not available")
            return
        try:
            math_cfg = self.config.get("math", {})
            obs = math_cfg.get("observatory", {})
            dome = math_cfg.get("dome", {})
            mount = math_cfg.get("mount", {})
            self.math_utils = MathUtils(
                latitude=obs.get("latitude", 0.0),
                longitude=obs.get("longitude", 0.0),
                elevation=obs.get("elevation", 0),
                dome_radius=dome.get("radius", 2.5),
                pier_height=mount.get("pier_height", 1.5),
                gem_offset_east=mount.get("gem_offset_east", 0.0),
                gem_offset_north=mount.get("gem_offset_north", 0.0),
            )
        except Exception as exc:
            logger.error("Failed to initialize MathUtils: %s", exc)

    def _auto_setup_ascom(self):
        """Prompt the user to choose an ASCOM telescope if none is configured."""
        if ASCOMHandler is None:
            return
        ascom_cfg = self.config.get("ascom", {})
        prog_id = ascom_cfg.get("telescope_prog_id", "")
        default_id = DEFAULT_CONFIG["ascom"]["telescope_prog_id"]
        if not prog_id or prog_id == default_id:
            logger.info("No custom telescope configured – launching chooser")
            try:
                chosen = ASCOMHandler.choose_device(prog_id or default_id)
            except Exception as exc:
                logger.warning("ASCOM chooser failed: %s", exc)
                return
            if chosen:
                self.config.setdefault("ascom", {})["telescope_prog_id"] = chosen
                save_config(self.config)
                logger.info("Telescope ProgID set to %s", chosen)

    def _sync_site_data(self):
        """Sync observatory coordinates from the mount if available."""
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
                logger.info("Synced observatory location from mount GPS")
        except Exception as exc:
            logger.warning("Could not sync site data from mount: %s", exc)

    def _init_ascom(self):
        """Connect to the ASCOM telescope driver (if available)."""
        if ASCOMHandler is None:
            logger.warning("ASCOM module not available – skipping telescope")
            return
        try:
            ascom_cfg = self.config.get("ascom", {})
            prog_id = ascom_cfg.get(
                "telescope_prog_id", "ASCOM.Simulator.Telescope"
            )
            self.ascom = ASCOMHandler(prog_id)
            if not self.ascom.connect():
                logger.warning(
                    "ASCOM connection failed – falling back to simulation"
                )
                self.ascom = None
        except Exception as exc:
            logger.error("Failed to initialize ASCOM: %s", exc)
            self.ascom = None

    def _init_serial(self):
        """Open the serial port to the Arduino motor controller."""
        if SerialController is None:
            logger.warning(
                "Serial module not available – skipping motor control"
            )
            return
        try:
            hw_cfg = self.config.get("hardware", {})
            self.serial = SerialController(
                port=hw_cfg.get("serial_port", "COM3"),
                baud_rate=hw_cfg.get("baud_rate", 9600),
                timeout=hw_cfg.get("timeout", 1.0),
            )
            if not self.serial.connect():
                logger.warning(
                    "Serial connection failed – falling back to simulation"
                )
                self.serial = None
        except Exception as exc:
            logger.error("Failed to initialize SerialController: %s", exc)
            self.serial = None

    def _init_vision(self):
        """Initialise the vision system, with camera auto-discovery fallback."""
        if VisionSystem is None:
            logger.warning("Vision module not available – skipping camera")
            return
        try:
            vis_cfg = self.config.get("vision", {})
            res = vis_cfg.get("resolution", {})
            aruco_cfg = vis_cfg.get("aruco", {})
            self.vision = VisionSystem(
                camera_index=vis_cfg.get("camera_index", 0),
                resolution=(res.get("width", 1280), res.get("height", 720)),
                aruco_dict=aruco_cfg.get("dictionary", "DICT_4X4_50"),
                marker_size=aruco_cfg.get("marker_size", 0.05),
            )
            if not self.vision.open_camera():
                logger.warning(
                    "Configured camera not found. Scanning..."
                )
                found = VisionSystem.find_working_camera()
                if found is not None:
                    self.config.setdefault("vision", {})["camera_index"] = found
                    self.vision = VisionSystem(
                        camera_index=found,
                        resolution=(res.get("width", 1280), res.get("height", 720)),
                        aruco_dict=aruco_cfg.get("dictionary", "DICT_4X4_50"),
                        marker_size=aruco_cfg.get("marker_size", 0.05),
                    )
                    if self.vision.open_camera():
                        save_config(self.config)
                        logger.info("Auto-discovered camera at index %d", found)
                    else:
                        self.vision = None
                else:
                    logger.warning("No working camera found – vision disabled")
                    self.vision = None
        except Exception as exc:
            logger.error("Failed to initialize VisionSystem: %s", exc)
            self.vision = None

    def _init_voice(self):
        """Initialise the voice assistant (if available)."""
        self.voice = None
        if VoiceAssistant is None:
            logger.warning("Voice module not available – skipping TTS")
            return
        try:
            self.voice = VoiceAssistant()
        except Exception as exc:
            logger.error("Failed to initialize VoiceAssistant: %s", exc)

    def _init_dome_driver(self):
        """Create the dome driver from the current configuration."""
        self.dome_driver = None
        if create_driver is None:
            logger.warning("Dome drivers module not available – skipping")
            return
        try:
            self.dome_driver = create_driver(self.config, self.serial)
        except Exception as exc:
            logger.error("Failed to initialize dome driver: %s", exc)

    # ---- Alpaca-facing properties / dome commands -------------------------
    @property
    def current_azimuth(self) -> float:
        """Current dome azimuth in degrees [0, 360)."""
        if self.dome_driver is not None:
            return self.dome_driver.position
        return self.sensor.get_azimuth()

    @property
    def is_slewing(self) -> bool:
        """``True`` while the dome is actively moving."""
        if self.dome_driver is not None:
            return self.dome_driver.slewing
        return abs(self.sensor.slew_rate) > 1e-6

    @property
    def is_parked(self) -> bool:
        return self._is_parked

    def move_dome(self, target_az: float) -> None:
        """Command the dome to slew to *target_az* (degrees)."""
        target_az = normalize_azimuth(target_az)
        self._is_parked = False
        speed = self.config.get("control", {}).get("max_speed", 100)
        if self.dome_driver is not None:
            self.dome_driver.slew_to(target_az, speed)
        elif self.serial:
            self.serial.move_to_azimuth(target_az, speed)
        logger.info("Move dome to %.1f°", target_az)

    def stop_dome(self) -> None:
        """Immediately stop any dome movement."""
        if self.dome_driver is not None:
            self.dome_driver.abort()
        if self.serial:
            self.serial.stop_motor()
        self.sensor.slew_rate = 0.0
        logger.info("Dome stopped")

    def park_dome(self) -> None:
        """Park the dome at azimuth 0° (north)."""
        self.move_dome(0.0)
        self._is_parked = True
        logger.info("Dome parking at 0°")

    def home_dome(self) -> None:
        """Run a homing (reference) sequence using config parameters."""
        homing = self.config.get("hardware", {}).get("homing", {})
        if not homing.get("enabled", False):
            logger.warning("Homing is not enabled in configuration")
            return
        home_az = homing.get("azimuth", 0.0)
        direction = homing.get("direction", "CW")
        if self.dome_driver is not None:
            self.dome_driver.home(home_az, direction)
        logger.info("Homing complete – position set to %.1f°", home_az)

    def _update_indicators(self):
        """Push current hardware status to the GUI indicator badges and hints."""
        if self.gui is None:
            return
        try:
            ascom_ok = self.ascom is not None and self.ascom.connected
            vision_ok = self.vision is not None and self.vision.camera_open
            motor_ok = self.serial is not None and self.serial.connected

            self.gui.set_indicator("ascom", ascom_ok)
            self.gui.set_indicator("vision", vision_ok)
            self.gui.set_indicator("motor", motor_ok)

            # Update user-facing hint labels
            if ascom_ok:
                self.gui.set_status_hint("ascom", t("gui.connected"))
            elif self.ascom is None:
                self.gui.set_status_hint("ascom", t("gui.not_connected"))
            else:
                self.gui.set_status_hint("ascom", t("gui.reconnecting"))

            if vision_ok:
                self.gui.set_status_hint("vision", t("gui.connected"))
            elif self.vision is None:
                self.gui.set_status_hint("vision", t("gui.no_camera_found"))
            else:
                self.gui.set_status_hint("vision", t("gui.reconnecting"))

            if motor_ok:
                self.gui.set_status_hint("motor", t("gui.connected"))
            elif self.serial is None:
                self.gui.set_status_hint("motor", t("gui.not_connected"))
            else:
                self.gui.set_status_hint("motor", t("gui.reconnecting"))

            # Update the top-level connection banner
            self.gui.update_connection_banner(ascom_ok, vision_ok, motor_ok)
        except Exception:
            pass

    # ---- Camera preview for the GUI ------------------------------------
    PREVIEW_INTERVAL = 0.2  # max ~5 fps for camera preview

    def __init_preview_state(self):
        """Lazily initialise preview timing state."""
        if not hasattr(self, "_last_preview_time"):
            self._last_preview_time = 0.0

    def _update_camera_preview(self) -> None:
        """Capture a frame with overlay and push it to the GUI preview."""
        self.__init_preview_state()
        import time as _time
        now = _time.time()
        if now - self._last_preview_time < self.PREVIEW_INTERVAL:
            return
        self._last_preview_time = now

        if self.gui is None:
            return

        if self.vision is None or not self.vision.camera_open:
            # Show placeholder when no camera
            self.gui.update_camera_preview(None)
            return

        frame = self.vision.capture_frame()
        if frame is None:
            self.gui.update_camera_preview(None)
            return

        # Detect markers for overlay
        marker_data = self.vision.detect_markers(frame)
        drift = None
        if marker_data:
            shape = marker_data.get("frame_shape")
            if shape:
                expected = (shape[1] / 2, shape[0] / 2)
            else:
                res = self.vision.resolution
                expected = (res[0] / 2, res[1] / 2)
            drift = self.vision.calculate_drift(marker_data, expected)

        _telem = {
            "mount_az": getattr(self, '_last_mount_az', None),
            "dome_az": self.sensor.get_azimuth(),
            "error": None,
            "mode": self.mode,
            "health": self._health,
        }
        if _telem["mount_az"] is not None and _telem["dome_az"] is not None:
            _err = _telem["mount_az"] - _telem["dome_az"]
            if _err > 180:
                _err -= 360
            elif _err < -180:
                _err += 360
            _telem["error"] = _err
        self.gui.update_camera_preview(frame, marker_data, drift, telemetry=_telem)

    # ---- Health checks --------------------------------------------------
    def check_system_health(self) -> str:
        """Evaluate system health and return HEALTHY / DEGRADED / CRITICAL.

        * **HEALTHY**: ASCOM + Serial + Vision all available.
        * **DEGRADED**: Vision lost, but ASCOM + Serial still work.
        * **CRITICAL**: ASCOM or Serial unavailable – motors must stop.
        """
        ascom_ok = self.ascom is not None and self.ascom.connected
        serial_ok = self.serial is not None and self.serial.connected
        vision_ok = self.vision is not None and self.vision.camera_open

        if ascom_ok and serial_ok and vision_ok:
            new_health = HEALTH_HEALTHY
        elif ascom_ok and serial_ok:
            new_health = HEALTH_DEGRADED
        else:
            new_health = HEALTH_CRITICAL

        if new_health != self._health:
            logger.warning("Health state changed: %s -> %s", self._health, new_health)
            self._health = new_health

        return new_health

    # ---- Periodic hardware reconnection ---------------------------------
    _RECONNECT_INTERVAL = 10.0  # seconds between reconnection attempts

    def _try_reconnect_hardware(self) -> None:
        """Attempt to reconnect disconnected hardware components.

        Called periodically from the control loop so that newly attached
        devices are detected automatically without restarting the app.
        """
        # ASCOM telescope
        if (self.ascom is None or not self.ascom.connected) and ASCOMHandler is not None:
            try:
                ascom_cfg = self.config.get("ascom", {})
                prog_id = ascom_cfg.get(
                    "telescope_prog_id", "ASCOM.Simulator.Telescope"
                )
                handler = ASCOMHandler(prog_id)
                if handler.connect():
                    self.ascom = handler
                    logger.info("ASCOM telescope reconnected")
                    if self.gui:
                        self.gui.write_log("✓ Telescope connected")
            except Exception:
                pass

        # Serial motor controller
        if (self.serial is None or not self.serial.connected) and SerialController is not None:
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
                    if self.gui:
                        self.gui.write_log("✓ Motor controller connected")
            except Exception:
                pass

        # Vision / camera
        if (self.vision is None or not self.vision.camera_open) and VisionSystem is not None:
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
                    if self.gui:
                        self.gui.write_log("✓ Camera connected")
            except Exception:
                pass

    # ---- Outlier rejection (vision drift) -------------------------------
    def _filter_drift(self, drift_az: float) -> Optional[float]:
        """Apply outlier rejection to a vision-derived azimuth correction.

        * If the value jumps by more than 5° from the last accepted value,
          treat it as a glitch and start a stability counter.
        * Accept the new value only after it has been stable (within 1°)
          for 3 consecutive frames.

        Returns:
            The accepted drift azimuth, or ``None`` to skip this frame.
        """
        glitch_threshold = 5.0
        stability_tolerance = 1.0
        required_stable_frames = 3

        if self._last_drift_az is None:
            self._last_drift_az = drift_az
            return drift_az

        delta = abs(drift_az - self._last_drift_az)

        if delta <= glitch_threshold:
            # Normal change – accept immediately
            self._last_drift_az = drift_az
            self._pending_drift_az = None
            self._stable_drift_count = 0
            return drift_az

        # Potentially a glitch – require stability before accepting
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

        logger.debug(
            "Vision glitch rejected (delta=%.1f°, stable=%d/%d)",
            delta, self._stable_drift_count, required_stable_frames,
        )
        return None

    def _check_vision_markers(self) -> bool:
        """Capture a frame and return whether markers are visible.

        Returns:
            ``True`` when at least one ArUco marker is detected,
            ``False`` when capture fails or no markers are found.
        """
        if self.vision is None:
            return True  # no camera ⇒ no lost signal
        frame = self.vision.capture_frame()
        if frame is None:
            return False
        markers = self.vision.detect_markers(frame)
        return bool(markers)

    # ---- Mode management (thread-safe) ----------------------------------
    def on_mode_changed(self, value: str):
        """Handle mode change from GUI segmented button."""
        with self._lock:
            self._mode = value
        logger.info("Mode changed to %s", value)

    @property
    def mode(self) -> str:
        """Return the current operating mode (thread-safe)."""
        with self._lock:
            return self._mode

    # ---- Button handlers (MANUAL mode) ----------------------------------
    def on_move_left(self):
        """Rotate counter-clockwise (only in MANUAL mode)."""
        if self.mode != "MANUAL":
            return
        self.sensor.slew_rate = -3.0
        if self.serial:
            self.serial.send_command("CCW 3")

    def on_stop(self):
        """Stop rotation (works in any mode)."""
        self.sensor.slew_rate = 0.0
        if self.serial:
            self.serial.stop_motor()

    def on_move_right(self):
        """Rotate clockwise (only in MANUAL mode)."""
        if self.mode != "MANUAL":
            return
        self.sensor.slew_rate = 3.0
        if self.serial:
            self.serial.send_command("CW 3")

    # ---- Simulation controls --------------------------------------------
    def _on_sim_az_changed(self, value: float) -> None:
        """Handle simulated telescope azimuth slider change."""
        self._sim_mount_az = float(value)

    def _on_sim_alt_changed(self, value: float) -> None:
        """Handle simulated telescope altitude slider change."""
        self._sim_mount_alt = float(value)

    def _on_sim_slit_toggle(self) -> None:
        """Toggle the simulated slit open/closed state."""
        self._sim_slit_open = not self._sim_slit_open
        if self.gui is not None:
            from localization import t
            self.gui.set_slit_status(self._sim_slit_open)
            self.gui.btn_sim_slit.content = ft.Text(
                t("gui.close_slit") if self._sim_slit_open
                else t("gui.open_slit")
            )
            self.gui.btn_sim_slit.icon = (
                ft.Icons.CLOSE if self._sim_slit_open
                else ft.Icons.OPEN_IN_BROWSER
            )

    # ---- Background control loop ----------------------------------------
    def _control_loop(self):
        """Thread-safe control loop that drives MANUAL and AUTO-SLAVE.

        The entire loop body is wrapped in a try/except so that any
        unexpected error triggers an emergency motor stop rather than
        letting the dome continue to rotate uncontrolled.
        """
        ctrl_cfg = self.config.get("control", {})
        update_rate = ctrl_cfg.get("update_rate", 10)
        interval = 1.0 / max(update_rate, 1)
        correction_threshold = ctrl_cfg.get("correction_threshold", 0.5)
        max_speed = ctrl_cfg.get("max_speed", 100)
        proportional_gain = ctrl_cfg.get("proportional_gain", 2.0)
        drift_enabled = ctrl_cfg.get("drift_correction_enabled", True)

        last = time.time()
        mount_az = 180.0  # default when ASCOM is unavailable
        mount_alt = 45.0

        while self._running:
          try:
            now = time.time()
            dt = now - last
            last = now

            current_mode = self.mode

            # -- Periodic hardware reconnection ---------------------------
            if now - self._last_reconnect_time >= self._RECONNECT_INTERVAL:
                self._last_reconnect_time = now
                self._try_reconnect_hardware()

            # -- Health check (cyclic) ------------------------------------
            health = self.check_system_health()
            if health == HEALTH_CRITICAL and current_mode == "AUTO-SLAVE":
                logger.critical("CRITICAL: ASCOM or Serial lost – stopping motors")
                if self.serial:
                    try:
                        self.serial.stop_motor()
                    except Exception:
                        pass
                self.sensor.slew_rate = 0.0

            # Track whether vision saw a marker this tick (avoids double capture)
            vision_ok = True
            vision_checked = False

            # Extended telemetry defaults
            sidereal_time = None
            tracking_rate = None
            pier_side = None

            if current_mode == "AUTO-SLAVE" and health != HEALTH_CRITICAL:
                # Step 1 – telescope position
                telescope_data = None
                if self.ascom:
                    telescope_data = self.ascom.get_all_data()

                if telescope_data and self.math_utils:
                    mount_az = telescope_data.get("azimuth", mount_az)
                    mount_alt = telescope_data.get("altitude", mount_alt)
                    self._last_mount_az = mount_az

                    # Extended telemetry from ASCOM
                    sidereal_time = telescope_data.get("sidereal_time")
                    tracking_rate = telescope_data.get("tracking_rate")
                    pier_side = telescope_data.get("side_of_pier")

                    # Step 2 – target dome azimuth
                    target_az = self.math_utils.calculate_required_azimuth(
                        ra=telescope_data["ra"],
                        dec=telescope_data["dec"],
                        side_of_pier=telescope_data.get("side_of_pier"),
                    )
                    target_az = normalize_azimuth(target_az)

                    # Step 3 – vision drift correction (only if HEALTHY)
                    if drift_enabled and self.vision and health == HEALTH_HEALTHY:
                        frame = self.vision.capture_frame()
                        vision_checked = True
                        if frame is not None:
                            markers = self.vision.detect_markers(frame)
                            vision_ok = bool(markers)
                            if markers:
                                shape = markers.get("frame_shape")
                                if shape:
                                    expected = (shape[1] / 2, shape[0] / 2)
                                else:
                                    res = self.vision.resolution
                                    expected = (res[0] / 2, res[1] / 2)
                                drift = self.vision.calculate_drift(
                                    markers, expected
                                )
                                if drift:
                                    corrected = (
                                        self.math_utils.apply_drift_correction(
                                            target_az, drift
                                        )
                                    )
                                    corrected = normalize_azimuth(corrected)
                                    # Outlier rejection
                                    accepted = self._filter_drift(corrected)
                                    if accepted is not None:
                                        target_az = accepted
                        else:
                            vision_ok = False

                    elif health == HEALTH_DEGRADED:
                        if self._last_vision_ok:
                            logger.warning("Running in blind mode (math only)")

                    # Step 5 – send MOVE command with hysteresis
                    dome_az = self.sensor.get_azimuth()
                    error = abs(target_az - dome_az)
                    if error > 180:
                        error = 360 - error
                    if error > correction_threshold and self.serial:
                        speed = min(int(error * proportional_gain), max_speed)
                        self.serial.move_to_azimuth(target_az, speed)

            # Simulation sensor always ticks (all modes)
            self.sensor.update(dt)
            dome_az = self.sensor.get_azimuth()

            # -- Simulation mode: if no real ASCOM, use slider values -----
            if self.ascom is None and current_mode == "MANUAL":
                mount_az = self._sim_mount_az
                mount_alt = self._sim_mount_alt
                # In simulation, dome follows telescope with a proportional slew
                sim_error = mount_az - dome_az
                if sim_error > 180:
                    sim_error -= 360
                elif sim_error < -180:
                    sim_error += 360
                if abs(sim_error) > correction_threshold and not self.serial:
                    sim_speed = min(abs(sim_error) * 2.0, 10.0)
                    self.sensor.slew_rate = sim_speed if sim_error > 0 else -sim_speed
                elif abs(sim_error) <= correction_threshold:
                    if abs(self.sensor.slew_rate) > 0 and not self.serial:
                        # Only auto-stop when simulation is driving
                        pass

            # -- Voice feedback: Moving → Stopped -------------------------
            current_status = "Moving" if abs(self.sensor.slew_rate) > 1e-6 else "Stopped"
            if self._last_status == "Moving" and current_status == "Stopped":
                if self.voice:
                    self.voice.say("Target reached")
            self._last_status = current_status

            # -- Voice feedback: Vision marker lost -----------------------
            if not vision_checked and drift_enabled:
                vision_ok = self._check_vision_markers()
            if self.vision:
                if self._last_vision_ok and not vision_ok:
                    logger.warning("Vision contact lost")
                    if self.voice:
                        self.voice.say("Visual contact lost")
            self._last_vision_ok = vision_ok

            # Push telemetry and camera preview to GUI
            if self.gui is not None:
                try:
                    self.gui.update_telemetry(
                        mount_az, dome_az,
                        mount_alt=mount_alt,
                        sidereal_time=sidereal_time,
                        tracking_rate=tracking_rate,
                        pier_side=pier_side,
                    )
                    self.gui.set_slit_status(self._sim_slit_open)
                    self._update_indicators()
                    self._update_camera_preview()
                    self.gui.batch_update()
                except Exception:
                    pass

            time.sleep(interval)
          except Exception:
            # Failsafe: any unexpected error in the loop body must stop
            # all motors immediately to prevent uncontrolled dome rotation.
            logger.critical(
                "Control loop error – EMERGENCY STOP", exc_info=True,
            )
            self._emergency_stop()
            if self.gui is not None:
                try:
                    self.gui.write_log(
                        "⚠ EMERGENCY STOP – control loop error (see log)"
                    )
                except Exception:
                    pass

    # ---- Safe dome slewing (collision avoidance) --------------------------
    def safe_slew_dome(self, target_dome_az: float) -> None:
        """Slew the dome to *target_dome_az* while avoiding telescope collision.

        When ``safety.telescope_protrudes`` is ``True`` and the required
        rotation exceeds ``max_nudge_while_protruding``, the telescope is
        first parked at the safe altitude before the dome rotates.
        """
        safety = self.config.get("safety", {})
        protrudes = safety.get("telescope_protrudes", False)
        safe_alt = safety.get("safe_altitude", 90.0)
        max_nudge = safety.get("max_nudge_while_protruding", 2.0)

        dome_az = self.sensor.get_azimuth()
        delta = abs(target_dome_az - dome_az)
        if delta > 180:
            delta = 360 - delta

        if protrudes and delta > max_nudge:
            # Step 1 – Park telescope at safe altitude
            if self.ascom and hasattr(self.ascom, "telescope") and self.ascom.telescope:
                try:
                    self.ascom.telescope.SlewToAltAz(dome_az, safe_alt)
                    while self.ascom.telescope.Slewing:
                        time.sleep(0.5)
                except Exception as exc:
                    logger.warning("Failed to park telescope: %s", exc)

            # Step 2 – Slew dome
            if self.serial:
                self.serial.move_to_azimuth(target_dome_az, 50)
            # Wait for dome (simulation)
            for _ in range(200):
                curr = self.sensor.get_azimuth()
                if abs(curr - target_dome_az) < 1.0:
                    break
                time.sleep(0.1)
        else:
            # Small correction – move dome directly
            if self.serial:
                self.serial.move_to_azimuth(target_dome_az, 50)

    # ---- Calibration mode -----------------------------------------------
    def run_calibration(self) -> Optional[dict]:
        """Run a 4-point calibration sequence and solve mount offsets.

        Drives the telescope/dome to four cardinal directions at 45° altitude,
        uses ``safe_slew_dome`` for collision avoidance, then solves for
        the best-fit GEM offsets.

        Returns:
            Dictionary with solved offsets, or ``None`` on failure.
        """
        if OffsetSolver is None:
            logger.error("Calibration module not available")
            return None
        if self.ascom is None:
            logger.error("ASCOM required for calibration")
            return None

        solver = OffsetSolver()
        cal_points = [
            (0.0, 45.0),    # North
            (90.0, 45.0),   # East
            (180.0, 45.0),  # South
            (270.0, 45.0),  # West
        ]

        old_mode = self.mode
        with self._lock:
            self._mode = "CALIBRATION"

        try:
            for az, alt in cal_points:
                # Park telescope, then slew dome
                self.safe_slew_dome(az)

                # Slew telescope to target alt/az
                if hasattr(self.ascom, "telescope") and self.ascom.telescope:
                    try:
                        self.ascom.telescope.SlewToAltAz(az, alt)
                        while self.ascom.telescope.Slewing:
                            time.sleep(0.5)
                    except Exception as exc:
                        logger.warning("Telescope slew failed at az=%s: %s", az, exc)
                        continue

                # Vision check – get dome slit az from sensor
                dome_az = self.sensor.get_azimuth()
                solver.add_point(az, alt, dome_az)
                logger.info(
                    "Calibration point: tel_az=%.1f, tel_alt=%.1f, dome_az=%.1f",
                    az, alt, dome_az,
                )

            result = solver.solve()
            if result is not None:
                mount = self.config.setdefault("math", {}).setdefault("mount", {})
                mount["gem_offset_east"] = result["gem_offset_east"]
                mount["gem_offset_north"] = result["gem_offset_north"]
                mount["pier_height"] = result["pier_height"]
                save_config(self.config)
                logger.info("Calibration complete – offsets saved: %s", result)
            return result
        finally:
            with self._lock:
                self._mode = old_mode

    # ---- Demo / Replay mode ---------------------------------------------
    def _run_demo_sequence(self, csv_path: str, speed: float = 1.0) -> None:
        """Play back a recorded session from a CSV file.

        During replay the real ASCOM handler is temporarily replaced
        with a :class:`ReplayASCOMHandler` so the normal control loop
        processes the recorded data as if the mount were moving live.

        Args:
            csv_path: Path to a calibration CSV file.
            speed:    Playback speed multiplier (default 1×).
        """
        if load_calibration_data is None or ReplayASCOMHandler is None:
            logger.error("Replay modules not available")
            return

        data = load_calibration_data(csv_path)
        if not data:
            logger.error("No data loaded from %s", csv_path)
            return

        replay = ReplayASCOMHandler(data, speed=speed)

        # Hot-swap: save real handler and inject replay handler
        self.real_ascom = getattr(self, "real_ascom", None) or self.ascom
        self.ascom = replay
        logger.info("DEMO MODE: Replay started from %s (%d records)", csv_path, len(data))

        try:
            # Update GUI status if available
            if self.gui is not None:
                try:
                    self.gui.write_log("REPLAY: [Orion Nebula]")
                except Exception:
                    pass

            # Voice announcement for status changes
            last_status = None

            # Let the normal control loop run while replaying
            duration = replay.data_duration / speed
            start = time.time()
            while time.time() - start < duration and self._running:
                # Check for status changes and trigger voice
                current_status = replay.current_status
                if current_status != last_status:
                    logger.info("REPLAY STATUS: %s", current_status)
                    if self.voice and current_status in ("SLEWING", "TRACKING"):
                        try:
                            self.voice.say(current_status.replace("_", " ").title())
                        except Exception:
                            pass
                    last_status = current_status
                time.sleep(0.5)
        finally:
            # Restore original handler
            self.ascom = self.real_ascom
            self.real_ascom = None
            logger.info("DEMO MODE: Replay finished – original ASCOM restored")

    # ---- Cleanup --------------------------------------------------------
    def shutdown(self):
        """Release all hardware resources and stop the control loop."""
        self._running = False
        if hasattr(self, '_alpaca') and self._alpaca:
            try:
                self._alpaca.shutdown()
            except Exception:
                pass
        if self.ascom:
            try:
                self.ascom.disconnect()
            except Exception:
                pass
        if self.serial:
            try:
                self.serial.disconnect()
            except Exception:
                pass
        if self.vision:
            try:
                self.vision.close_camera()
            except Exception:
                pass


    # ---- Settings callback ------------------------------------------------
    def _on_settings_saved(self, new_config: dict) -> None:
        """Handle updated config from the settings dialog."""
        self.config = new_config
        logger.info("Configuration updated from settings dialog")

    # ---- Diagnostics callback ---------------------------------------------
    def _run_diagnostics(self) -> None:
        """Run system diagnostics and show results in the GUI.

        Shows a loading dialog immediately, then runs diagnostics in a
        background thread to keep the UI responsive.
        """
        if self.gui is None:
            return

        # Show loading dialog immediately
        dlg = self.gui.show_diagnostics_loading()

        def _bg_diagnostics():
            try:
                from diagnostics import SystemDiagnostics
                diag = SystemDiagnostics(self.config, controller=self)
                report = diag.run_all()
                self.gui.show_diagnostics(report, dlg=dlg)
            except Exception as exc:
                logger.error("Diagnostics failed: %s", exc)

        threading.Thread(target=_bg_diagnostics, daemon=True).start()


def main(page: ft.Page):
    """Flet main entry point – configures the page and starts the controller."""
    page.title = "ARGUS – Dome Control"
    page.bgcolor = COLOR_BG
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1280
    page.window.height = 720

    # -- Splash screen with progress bar ----------------------------------
    splash_title = ft.Text(
        "ARGUS", size=36, weight=ft.FontWeight.BOLD,
        color="#CCCCCC", text_align=ft.TextAlign.CENTER,
        font_family="RobotoMono",
    )
    splash_subtitle = ft.Text(
        "Advanced Rotation Guidance Using Sensors",
        size=13, color="#666666", text_align=ft.TextAlign.CENTER,
    )
    loading_bar = ft.ProgressBar(width=320, value=0, color=ft.Colors.CYAN)
    loading_text = ft.Text(
        "Starting up …",
        size=12, color="#888888", text_align=ft.TextAlign.CENTER,
    )
    loading_overlay = ft.Container(
        content=ft.Column(
            [splash_title, splash_subtitle,
             ft.Container(height=24),
             loading_bar, loading_text],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        alignment=ft.Alignment(0, 0),
        expand=True,
        bgcolor=COLOR_BG,
    )
    page.add(loading_overlay)
    page.update()

    def _update_splash(progress: float, text: str):
        """Update splash screen progress (0.0–1.0) and status text."""
        loading_bar.value = progress
        loading_text.value = text
        try:
            page.update()
        except Exception:
            pass

    def _deferred_init():
        """Run heavy hardware initialisation in a background thread."""
        try:
            _update_splash(0.05, t("splash.loading_config"))
            config = load_config()

            _update_splash(0.10, t("splash.building_ui"))
            # Apply language from config
            lang = config.get("language", "en")
            try:
                set_language(lang)
            except Exception:
                pass

            # Build GUI without mounting – the splash is still on the page
            gui = ArgusGUI(page, auto_mount=False)
            page._argus_gui = gui

            _SPLASH_STEP_DELAY = 0.1  # seconds between splash steps

            _update_splash(0.20, t("splash.init_math"))
            time.sleep(_SPLASH_STEP_DELAY)

            _update_splash(0.30, t("splash.init_ascom"))
            time.sleep(_SPLASH_STEP_DELAY)

            _update_splash(0.40, t("splash.init_serial"))
            time.sleep(_SPLASH_STEP_DELAY)

            _update_splash(0.50, t("splash.init_vision"))
            time.sleep(_SPLASH_STEP_DELAY)

            _update_splash(0.60, t("splash.init_voice"))
            controller = ArgusController(config=config, gui=gui)

            _update_splash(0.75, t("splash.start_alpaca"))
            # Start ASCOM Alpaca server (if available)
            alpaca = None
            if AlpacaDomeServer is not None:
                try:
                    alpaca = AlpacaDomeServer(controller)
                    alpaca.start()
                except Exception as exc:
                    logger.warning("Failed to start Alpaca server: %s", exc)

            _update_splash(0.85, t("splash.start_loop"))
            time.sleep(_SPLASH_STEP_DELAY * 1.5)

            page._argus_controller = controller
            page._argus_alpaca = alpaca

            _update_splash(1.0, t("splash.ready"))
            time.sleep(0.3)

            # Atomic splash → GUI transition: remove splash, mount GUI
            try:
                page.clean()
                gui.mount()
                page.update()
            except Exception:
                pass

        except Exception:
            logger.critical("Unhandled exception during init", exc_info=True)
            loading_text.value = "\u26a0 Initialisation failed \u2013 see log"
            loading_bar.color = "#C0392B"
            loading_bar.value = 1.0
            try:
                page.update()
            except Exception:
                pass

    threading.Thread(target=_deferred_init, name="argus-init", daemon=True).start()


if __name__ == "__main__":
    ft.run(main)
