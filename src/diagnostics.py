"""
ARGUS - Advanced Rotation Guidance Using Sensors
Diagnostics Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Comprehensive system diagnostics that help users troubleshoot hardware,
software, and configuration problems.  Each check returns a structured
result with a status, human-readable message, and actionable suggestion.
"""

import logging
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
class Status(Enum):
    """Outcome of a single diagnostic check."""
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"
    INFO = "INFO"


@dataclass
class DiagResult:
    """Result of a single diagnostic check."""
    category: str
    name: str
    status: Status
    message: str
    suggestion: str = ""


@dataclass
class DiagReport:
    """Complete diagnostics report."""
    results: List[DiagResult] = field(default_factory=list)
    timestamp: str = ""
    duration_s: float = 0.0

    @property
    def errors(self) -> List[DiagResult]:
        return [r for r in self.results if r.status == Status.ERROR]

    @property
    def warnings(self) -> List[DiagResult]:
        return [r for r in self.results if r.status == Status.WARNING]

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.status == Status.OK)

    @property
    def summary(self) -> str:
        total = len(self.results)
        ok = self.ok_count
        warn = len(self.warnings)
        err = len(self.errors)
        if err:
            return f"{err} error(s), {warn} warning(s), {ok}/{total} checks OK"
        if warn:
            return f"No errors, {warn} warning(s), {ok}/{total} checks OK"
        return f"All {total} checks passed"


# ---------------------------------------------------------------------------
# Diagnostics engine
# ---------------------------------------------------------------------------
class SystemDiagnostics:
    """Run comprehensive system diagnostics.

    Args:
        config: The application configuration dictionary.
        controller: Optional ``ArgusController`` instance for live checks.
    """

    def __init__(self, config: dict, controller=None):
        self.config = config
        self.controller = controller

    def run_all(self) -> DiagReport:
        """Execute every diagnostic check and return the full report."""
        import datetime
        start = time.monotonic()
        report = DiagReport(timestamp=datetime.datetime.now().isoformat())

        # Run all check categories
        report.results.extend(self._check_system())
        report.results.extend(self._check_python())
        report.results.extend(self._check_config())
        report.results.extend(self._check_ascom())
        report.results.extend(self._check_serial())
        report.results.extend(self._check_vision())
        report.results.extend(self._check_network())
        report.results.extend(self._check_disk())

        report.duration_s = round(time.monotonic() - start, 2)
        logger.info("Diagnostics completed in %.2fs: %s",
                     report.duration_s, report.summary)
        return report

    # ---- System / OS checks -----------------------------------------------
    def _check_system(self) -> List[DiagResult]:
        results: List[DiagResult] = []

        # OS info
        results.append(DiagResult(
            category="System", name="Operating System",
            status=Status.INFO,
            message=f"{platform.system()} {platform.release()} ({platform.machine()})",
        ))

        # Windows check (ASCOM requires Windows)
        if platform.system() != "Windows":
            results.append(DiagResult(
                category="System", name="Windows Required",
                status=Status.WARNING,
                message="ARGUS ASCOM features require Windows",
                suggestion="Run ARGUS on a Windows machine for full telescope control.",
            ))
        else:
            results.append(DiagResult(
                category="System", name="Windows Platform",
                status=Status.OK,
                message="Running on Windows – ASCOM compatible",
            ))

        return results

    # ---- Python environment checks ----------------------------------------
    def _check_python(self) -> List[DiagResult]:
        results: List[DiagResult] = []

        # Python version
        ver = sys.version_info
        results.append(DiagResult(
            category="Python", name="Python Version",
            status=Status.OK if ver >= (3, 8) else Status.ERROR,
            message=f"Python {ver.major}.{ver.minor}.{ver.micro}",
            suggestion="" if ver >= (3, 8) else "ARGUS requires Python 3.8+. Please upgrade.",
        ))

        # Critical modules
        modules = {
            "flet": "GUI framework",
            "yaml": "Configuration (pyyaml)",
            "numpy": "Math calculations",
            "cv2": "Camera / vision (opencv-python)",
            "serial": "Serial communication (pyserial)",
            "flask": "Alpaca REST server",
            "astropy": "Astronomy calculations",
            "scipy": "Calibration solver",
        }
        for mod, desc in modules.items():
            try:
                __import__(mod)
                results.append(DiagResult(
                    category="Python", name=f"Module: {mod}",
                    status=Status.OK, message=f"{desc} – installed",
                ))
            except ImportError:
                results.append(DiagResult(
                    category="Python", name=f"Module: {mod}",
                    status=Status.ERROR,
                    message=f"{desc} – NOT installed",
                    suggestion=f"Install with: pip install {mod}",
                ))

        # ASCOM module (Windows-only)
        if platform.system() == "Windows":
            try:
                import win32com.client  # noqa: F401
                results.append(DiagResult(
                    category="Python", name="Module: pywin32",
                    status=Status.OK,
                    message="ASCOM COM bridge – installed",
                ))
            except ImportError:
                results.append(DiagResult(
                    category="Python", name="Module: pywin32",
                    status=Status.ERROR,
                    message="ASCOM COM bridge – NOT installed",
                    suggestion="Install with: pip install pywin32",
                ))

        return results

    # ---- Configuration validation -----------------------------------------
    def _check_config(self) -> List[DiagResult]:
        results: List[DiagResult] = []

        # Config file exists
        from path_utils import resolve_path
        config_path = resolve_path("config.yaml")
        if config_path.is_file():
            results.append(DiagResult(
                category="Config", name="Config File",
                status=Status.OK, message=f"Found: {config_path}",
            ))
        else:
            results.append(DiagResult(
                category="Config", name="Config File",
                status=Status.WARNING,
                message=f"Not found: {config_path}",
                suggestion="Using default settings. Create config.yaml to customise.",
            ))

        # Observatory coordinates
        obs = self.config.get("math", {}).get("observatory", {})
        lat = obs.get("latitude", 0.0)
        lon = obs.get("longitude", 0.0)
        if lat == 0.0 and lon == 0.0:
            results.append(DiagResult(
                category="Config", name="Observatory Location",
                status=Status.WARNING,
                message="Latitude and longitude are both 0.0 (default)",
                suggestion="Set your observatory coordinates in Settings → Math "
                           "for accurate dome positioning.",
            ))
        elif not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            results.append(DiagResult(
                category="Config", name="Observatory Location",
                status=Status.ERROR,
                message=f"Invalid coordinates: lat={lat}, lon={lon}",
                suggestion="Latitude must be −90..90, longitude −180..180.",
            ))
        else:
            results.append(DiagResult(
                category="Config", name="Observatory Location",
                status=Status.OK,
                message=f"lat={lat:.4f}, lon={lon:.4f}",
            ))

        # Dome geometry
        dome = self.config.get("math", {}).get("dome", {})
        dome_r = dome.get("radius", 0)
        if dome_r <= 0:
            results.append(DiagResult(
                category="Config", name="Dome Radius",
                status=Status.WARNING,
                message=f"Dome radius is {dome_r} – seems invalid",
                suggestion="Set a positive dome radius in Settings → Math.",
            ))
        else:
            results.append(DiagResult(
                category="Config", name="Dome Radius",
                status=Status.OK, message=f"{dome_r} m",
            ))

        # Serial port config
        hw = self.config.get("hardware", {})
        port = hw.get("serial_port", "")
        if not port:
            results.append(DiagResult(
                category="Config", name="Serial Port",
                status=Status.WARNING,
                message="No serial port configured",
                suggestion="Set hardware.serial_port in config.yaml (e.g. COM3).",
            ))
        else:
            results.append(DiagResult(
                category="Config", name="Serial Port",
                status=Status.INFO, message=f"Configured: {port}",
            ))

        # Update rate
        ctrl = self.config.get("control", {})
        rate = ctrl.get("update_rate", 10)
        if rate < 1:
            results.append(DiagResult(
                category="Config", name="Update Rate",
                status=Status.ERROR,
                message=f"Update rate {rate} Hz is too low",
                suggestion="Set control.update_rate to at least 1 Hz.",
            ))
        elif rate > 60:
            results.append(DiagResult(
                category="Config", name="Update Rate",
                status=Status.WARNING,
                message=f"Update rate {rate} Hz is very high – may cause CPU load",
                suggestion="Consider lowering to 10–30 Hz unless needed.",
            ))
        else:
            results.append(DiagResult(
                category="Config", name="Update Rate",
                status=Status.OK, message=f"{rate} Hz",
            ))

        return results

    # ---- ASCOM / Telescope checks -----------------------------------------
    def _check_ascom(self) -> List[DiagResult]:
        results: List[DiagResult] = []

        if platform.system() != "Windows":
            results.append(DiagResult(
                category="ASCOM", name="ASCOM Platform",
                status=Status.INFO,
                message="Skipped – ASCOM is Windows-only",
            ))
            return results

        # Check ASCOM Platform installation
        try:
            import win32com.client
            chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
            results.append(DiagResult(
                category="ASCOM", name="ASCOM Platform",
                status=Status.OK,
                message="ASCOM Platform installed and accessible",
            ))
        except Exception as exc:
            results.append(DiagResult(
                category="ASCOM", name="ASCOM Platform",
                status=Status.ERROR,
                message=f"ASCOM Platform not accessible: {exc}",
                suggestion="Install ASCOM Platform from https://ascom-standards.org/Downloads",
            ))
            return results

        # Check configured telescope driver
        ascom_cfg = self.config.get("ascom", {})
        prog_id = ascom_cfg.get("telescope_prog_id", "")
        if prog_id:
            try:
                telescope = win32com.client.Dispatch(prog_id)
                results.append(DiagResult(
                    category="ASCOM", name="Telescope Driver",
                    status=Status.OK,
                    message=f"Driver '{prog_id}' loaded successfully",
                ))
                # Try connecting
                try:
                    telescope.Connected = True
                    if telescope.Connected:
                        results.append(DiagResult(
                            category="ASCOM", name="Telescope Connection",
                            status=Status.OK,
                            message="Telescope is responding",
                        ))
                        telescope.Connected = False
                    else:
                        results.append(DiagResult(
                            category="ASCOM", name="Telescope Connection",
                            status=Status.ERROR,
                            message="Telescope driver loaded but connection refused",
                            suggestion="Check that the telescope is powered on and the "
                                       "mount driver is configured correctly.",
                        ))
                except Exception as exc:
                    results.append(DiagResult(
                        category="ASCOM", name="Telescope Connection",
                        status=Status.ERROR,
                        message=f"Connection failed: {exc}",
                        suggestion="Ensure the telescope is powered on and connected. "
                                   "Try connecting with the ASCOM driver's own test tool.",
                    ))
            except Exception as exc:
                results.append(DiagResult(
                    category="ASCOM", name="Telescope Driver",
                    status=Status.ERROR,
                    message=f"Cannot load driver '{prog_id}': {exc}",
                    suggestion="Install the correct ASCOM driver for your telescope mount. "
                               "Check the ProgID in Settings → ASCOM.",
                ))
        else:
            results.append(DiagResult(
                category="ASCOM", name="Telescope Driver",
                status=Status.WARNING,
                message="No telescope driver configured",
                suggestion="Configure a telescope ProgID in Settings → ASCOM.",
            ))

        # Live controller state
        if self.controller and self.controller.ascom:
            connected = self.controller.ascom.connected
            results.append(DiagResult(
                category="ASCOM", name="Live Connection",
                status=Status.OK if connected else Status.ERROR,
                message="Connected" if connected else "Disconnected",
                suggestion="" if connected else "The telescope was connected "
                           "but lost connection. Check cables and power.",
            ))

        return results

    # ---- Serial / Motor checks --------------------------------------------
    def _check_serial(self) -> List[DiagResult]:
        results: List[DiagResult] = []

        # List available serial ports
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            if ports:
                port_names = [f"{p.device} ({p.description})" for p in ports]
                results.append(DiagResult(
                    category="Serial", name="Available Ports",
                    status=Status.OK,
                    message="; ".join(port_names),
                ))
            else:
                results.append(DiagResult(
                    category="Serial", name="Available Ports",
                    status=Status.WARNING,
                    message="No serial ports detected",
                    suggestion="Connect the Arduino motor controller via USB. "
                               "Check Device Manager for COM ports.",
                ))
        except ImportError:
            results.append(DiagResult(
                category="Serial", name="Available Ports",
                status=Status.ERROR,
                message="pyserial not installed – cannot scan ports",
                suggestion="Install with: pip install pyserial",
            ))
            return results

        # Check configured port
        hw = self.config.get("hardware", {})
        port = hw.get("serial_port", "COM3")
        port_exists = any(p.device == port for p in ports)

        if port_exists:
            results.append(DiagResult(
                category="Serial", name=f"Configured Port ({port})",
                status=Status.OK,
                message=f"Port {port} is available",
            ))
            # Try opening the port
            try:
                import serial as pyserial
                ser = pyserial.Serial(port, hw.get("baud_rate", 9600), timeout=1)
                ser.close()
                results.append(DiagResult(
                    category="Serial", name="Port Accessibility",
                    status=Status.OK,
                    message=f"{port} can be opened at {hw.get('baud_rate', 9600)} baud",
                ))
            except Exception as exc:
                results.append(DiagResult(
                    category="Serial", name="Port Accessibility",
                    status=Status.ERROR,
                    message=f"Cannot open {port}: {exc}",
                    suggestion="The port may be in use by another application. "
                               "Close other programs that use this COM port.",
                ))
        elif ports:
            available = ", ".join(p.device for p in ports)
            results.append(DiagResult(
                category="Serial", name=f"Configured Port ({port})",
                status=Status.ERROR,
                message=f"Port {port} not found. Available: {available}",
                suggestion=f"Change hardware.serial_port in Settings to one of: "
                           f"{available}",
            ))
        else:
            results.append(DiagResult(
                category="Serial", name=f"Configured Port ({port})",
                status=Status.ERROR,
                message=f"Port {port} not found and no ports available",
                suggestion="Connect the Arduino controller via USB.",
            ))

        # Motor type & protocol
        motor = hw.get("motor_type", "stepper")
        protocol = hw.get("protocol", "argus")
        results.append(DiagResult(
            category="Serial", name="Motor Configuration",
            status=Status.INFO,
            message=f"Type: {motor}, Protocol: {protocol}",
        ))

        # Live controller state
        if self.controller and self.controller.serial:
            connected = self.controller.serial.connected
            results.append(DiagResult(
                category="Serial", name="Live Connection",
                status=Status.OK if connected else Status.ERROR,
                message="Connected" if connected else "Disconnected",
                suggestion="" if connected else "The motor controller lost connection. "
                           "Check USB cable and try reconnecting.",
            ))

        return results

    # ---- Camera / Vision checks -------------------------------------------
    def _check_vision(self) -> List[DiagResult]:
        results: List[DiagResult] = []

        try:
            import cv2  # noqa: F401
        except ImportError:
            results.append(DiagResult(
                category="Vision", name="OpenCV",
                status=Status.ERROR,
                message="OpenCV not installed – camera features unavailable",
                suggestion="Install with: pip install opencv-python opencv-contrib-python",
            ))
            return results

        results.append(DiagResult(
            category="Vision", name="OpenCV",
            status=Status.OK,
            message=f"OpenCV {cv2.__version__} installed",
        ))

        # Scan for cameras
        vis_cfg = self.config.get("vision", {})
        configured_index = vis_cfg.get("camera_index", 0)
        found_cameras: list = []

        active_cam_idx = None
        if self.controller and self.controller.vision and self.controller.vision.camera_open:
            active_cam_idx = self.controller.vision.camera_index

        for i in range(5):
            if i == active_cam_idx:
                # Camera in use by the vision system – report without re-opening
                try:
                    frame = self.controller.vision.capture_frame()
                    if frame is not None:
                        h, w = frame.shape[:2]
                        found_cameras.append((i, w, h))
                except Exception:
                    pass
                continue
            cap = None
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        h, w = frame.shape[:2]
                        found_cameras.append((i, w, h))
            except Exception:
                pass
            finally:
                if cap is not None:
                    cap.release()

        if found_cameras:
            cam_info = [f"Camera {i} ({w}×{h})" for i, w, h in found_cameras]
            results.append(DiagResult(
                category="Vision", name="Available Cameras",
                status=Status.OK,
                message="; ".join(cam_info),
            ))
        else:
            results.append(DiagResult(
                category="Vision", name="Available Cameras",
                status=Status.WARNING,
                message="No cameras detected",
                suggestion="Connect a USB camera. Check that no other application "
                           "is using the camera.",
            ))

        # Check configured camera
        if any(i == configured_index for i, _, _ in found_cameras):
            results.append(DiagResult(
                category="Vision", name=f"Configured Camera ({configured_index})",
                status=Status.OK,
                message="Camera is available",
            ))
        elif found_cameras:
            avail = ", ".join(str(i) for i, _, _ in found_cameras)
            results.append(DiagResult(
                category="Vision", name=f"Configured Camera ({configured_index})",
                status=Status.WARNING,
                message=f"Camera index {configured_index} not found. Available: {avail}",
                suggestion=f"Change vision.camera_index in Settings to {found_cameras[0][0]}.",
            ))

        # ArUco dictionary check
        aruco_dict = vis_cfg.get("aruco", {}).get("dictionary", "DICT_4X4_50")
        valid_dicts = [
            "DICT_4X4_50", "DICT_4X4_100", "DICT_4X4_250", "DICT_4X4_1000",
            "DICT_5X5_50", "DICT_5X5_100", "DICT_5X5_250", "DICT_5X5_1000",
            "DICT_6X6_50", "DICT_6X6_100", "DICT_6X6_250", "DICT_6X6_1000",
        ]
        if aruco_dict in valid_dicts:
            results.append(DiagResult(
                category="Vision", name="ArUco Dictionary",
                status=Status.OK, message=aruco_dict,
            ))
        else:
            results.append(DiagResult(
                category="Vision", name="ArUco Dictionary",
                status=Status.ERROR,
                message=f"Unknown dictionary: {aruco_dict}",
                suggestion=f"Use one of: {', '.join(valid_dicts[:4])} …",
            ))

        # Live controller state
        if self.controller and self.controller.vision:
            cam_open = self.controller.vision.camera_open
            results.append(DiagResult(
                category="Vision", name="Live Camera",
                status=Status.OK if cam_open else Status.ERROR,
                message="Camera streaming" if cam_open else "Camera closed",
                suggestion="" if cam_open else "The camera was connected but lost. "
                           "Check USB cable.",
            ))

        return results

    # ---- Network checks ---------------------------------------------------
    def _check_network(self) -> List[DiagResult]:
        results: List[DiagResult] = []
        import socket

        # Alpaca server port
        alpaca_port = 11111
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", alpaca_port))
            sock.close()
            if result == 0:
                results.append(DiagResult(
                    category="Network", name="Alpaca Server",
                    status=Status.OK,
                    message=f"Alpaca server is running on port {alpaca_port}",
                ))
            else:
                results.append(DiagResult(
                    category="Network", name="Alpaca Server",
                    status=Status.WARNING,
                    message=f"Alpaca server not reachable on port {alpaca_port}",
                    suggestion="The Alpaca server may not have started. "
                               "Check firewall settings.",
                ))
        except Exception as exc:
            results.append(DiagResult(
                category="Network", name="Alpaca Server",
                status=Status.WARNING,
                message=f"Could not check Alpaca port: {exc}",
            ))

        return results

    # ---- Disk / file-system checks ----------------------------------------
    def _check_disk(self) -> List[DiagResult]:
        results: List[DiagResult] = []

        from path_utils import get_base_path, resolve_path
        base = get_base_path()

        # Writable check
        try:
            test_file = base / ".argus_diag_test"
            test_file.write_text("test")
            test_file.unlink()
            results.append(DiagResult(
                category="Disk", name="Write Access",
                status=Status.OK,
                message=f"Application directory is writable: {base}",
            ))
        except Exception:
            results.append(DiagResult(
                category="Disk", name="Write Access",
                status=Status.ERROR,
                message=f"Cannot write to application directory: {base}",
                suggestion="Run ARGUS from a directory with write permissions, "
                           "or run as administrator.",
            ))

        # Assets directory (may live beside the .exe or inside _internal/)
        assets = resolve_path("assets")
        if assets.is_dir():
            results.append(DiagResult(
                category="Disk", name="Assets Directory",
                status=Status.OK, message=f"Found: {assets}",
            ))
        else:
            results.append(DiagResult(
                category="Disk", name="Assets Directory",
                status=Status.WARNING,
                message=f"Assets directory not found: {assets}",
                suggestion="Themes and resources may be missing. "
                           "Re-extract the portable ZIP.",
            ))

        # Log file writable
        log_cfg = self.config.get("logging", {})
        log_file = log_cfg.get("file")
        if log_file:
            log_path = Path(log_file)
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a"):
                    pass
                results.append(DiagResult(
                    category="Disk", name="Log File",
                    status=Status.OK, message=f"Writable: {log_path}",
                ))
            except Exception:
                results.append(DiagResult(
                    category="Disk", name="Log File",
                    status=Status.WARNING,
                    message=f"Cannot write log file: {log_path}",
                    suggestion="Check file permissions or change logging.file in config.",
                ))

        return results
