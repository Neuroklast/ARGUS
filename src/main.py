"""
ARGUS - Advanced Rotation Guidance Using Sensors
Main Application Entry Point (Controller Pattern)

Loads config.yaml, initializes hardware modules, and provides
a state-machine-driven control loop for MANUAL and AUTO-SLAVE modes.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional

import yaml
import customtkinter as ctk

from gui import ArgusApp
from simulation_sensor import SimulationSensor

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

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------
def load_config(path: Optional[str] = None) -> dict:
    """Load configuration from a YAML file.

    Args:
        path: Path to config file.  Defaults to ``config.yaml`` in the
              repository root.

    Returns:
        Configuration dictionary (empty dict on error).
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        with open(config_path, "r") as fh:
            config = yaml.safe_load(fh)
        logger.info("Configuration loaded from %s", config_path)
        return config or {}
    except FileNotFoundError:
        logger.warning("Config file not found: %s – using defaults", config_path)
        return {}
    except yaml.YAMLError as exc:
        logger.error("Error parsing config file: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Main controller
# ---------------------------------------------------------------------------
class ArgusController:
    """Controller that bridges the GUI and hardware modules.

    Supports **MANUAL** and **AUTO-SLAVE** modes with graceful
    degradation when hardware components are unavailable.
    """

    def __init__(self, config: Optional[dict] = None):
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

        # -- Appearance (must be set before any widget is created) --------
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.app = ArgusApp()

        # Simulation fallback (always available)
        self.sensor = SimulationSensor()

        # Hardware handles (``None`` = unavailable)
        self.ascom = None
        self.serial = None
        self.vision = None
        self.math_utils = None

        self._init_math_utils()
        self._init_ascom()
        self._init_serial()
        self._init_vision()
        self._init_voice()

        # -- Bind GUI callbacks ------------------------------------------
        self.app.btn_ccw.configure(command=self.on_move_left)
        self.app.btn_stop.configure(command=self.on_stop)
        self.app.btn_cw.configure(command=self.on_move_right)
        self.app.mode_selector.configure(command=self.on_mode_changed)

        self._update_indicators()

        # -- Background control loop -------------------------------------
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()

    # ---- Logging --------------------------------------------------------
    def _setup_logging(self):
        """Configure the root logger from the ``logging`` config section."""
        log_cfg = self.config.get("logging", {})
        level = getattr(logging, log_cfg.get("level", "INFO"), logging.INFO)
        log_file = log_cfg.get("file")

        handlers = []
        if log_cfg.get("console", True):
            handlers.append(logging.StreamHandler())
        if log_file:
            handlers.append(logging.FileHandler(log_file))

        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=handlers or [logging.StreamHandler()],
        )

    # ---- Hardware initialisation helpers --------------------------------
    def _init_math_utils(self):
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

    def _init_ascom(self):
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
                logger.warning("Camera not found – vision system disabled")
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

    def _update_indicators(self):
        """Push current hardware status to the GUI indicator badges."""
        try:
            self.app.set_indicator(
                "ascom",
                self.ascom is not None and self.ascom.connected,
            )
            self.app.set_indicator(
                "vision",
                self.vision is not None and self.vision.camera_open,
            )
            self.app.set_indicator(
                "motor",
                self.serial is not None and self.serial.connected,
            )
        except RuntimeError:
            pass

    # ---- Mode management (thread-safe) ----------------------------------
    def on_mode_changed(self, value: str):
        """Handle mode change from GUI segmented button."""
        with self._lock:
            self._mode = value
        logger.info("Mode changed to: %s", value)

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

    # ---- Background control loop ----------------------------------------
    def _control_loop(self):
        """Thread-safe control loop that drives MANUAL and AUTO-SLAVE."""
        ctrl_cfg = self.config.get("control", {})
        update_rate = ctrl_cfg.get("update_rate", 10)
        interval = 1.0 / max(update_rate, 1)
        correction_threshold = ctrl_cfg.get("correction_threshold", 0.5)
        max_speed = ctrl_cfg.get("max_speed", 100)
        proportional_gain = ctrl_cfg.get("proportional_gain", 2.0)
        drift_enabled = ctrl_cfg.get("drift_correction_enabled", True)

        last = time.time()
        mount_az = 180.0  # default when ASCOM is unavailable

        while self._running:
            now = time.time()
            dt = now - last
            last = now

            current_mode = self.mode

            if current_mode == "AUTO-SLAVE":
                # Step 1 – telescope position
                telescope_data = None
                if self.ascom:
                    telescope_data = self.ascom.get_all_data()

                if telescope_data and self.math_utils:
                    mount_az = telescope_data.get("azimuth", mount_az)

                    # Step 2 – target dome azimuth
                    target_az = self.math_utils.calculate_required_azimuth(
                        ra=telescope_data["ra"],
                        dec=telescope_data["dec"],
                        side_of_pier=telescope_data.get("side_of_pier"),
                    )

                    # Step 3 – vision drift correction
                    if drift_enabled and self.vision:
                        frame = self.vision.capture_frame()
                        if frame is not None:
                            markers = self.vision.detect_markers(frame)
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
                                    # Step 4 – corrected target angle
                                    target_az = (
                                        self.math_utils.apply_drift_correction(
                                            target_az, drift
                                        )
                                    )

                    # Step 5 – send MOVE command if error exceeds threshold
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

            # -- Voice feedback: Moving → Stopped -------------------------
            current_status = "Moving" if abs(self.sensor.slew_rate) > 1e-6 else "Stopped"
            if self._last_status == "Moving" and current_status == "Stopped":
                if self.voice:
                    self.voice.say("Target reached")
            self._last_status = current_status

            # -- Voice feedback: Vision marker lost -----------------------
            vision_ok = True
            if self.vision:
                frame = self.vision.capture_frame() if drift_enabled else None
                if frame is not None:
                    markers = self.vision.detect_markers(frame)
                    vision_ok = bool(markers)
                else:
                    vision_ok = False
                if self._last_vision_ok and not vision_ok:
                    if self.voice:
                        self.voice.say("Visual contact lost")
            self._last_vision_ok = vision_ok

            # Push telemetry to GUI
            try:
                self.app.after(
                    0, self.app.update_telemetry, mount_az, dome_az
                )
                self.app.after(0, self._update_indicators)
            except RuntimeError:
                pass

            time.sleep(interval)

    # ---- Cleanup --------------------------------------------------------
    def shutdown(self):
        """Release all hardware resources and stop the control loop."""
        self._running = False
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


def main():
    """Main entry point."""
    config = load_config()
    controller = ArgusController(config)
    controller.app.mainloop()
    controller.shutdown()


if __name__ == "__main__":
    main()
