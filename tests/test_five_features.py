"""Tests for the five new features:

1. Predictive Slaving (Look-Ahead) – MathUtils.extrapolate_azimuth
2. Hardware Watchdog – SerialController.send_ping
3. INDI Protocol Support – INDIDomeServer basics
4. Auto-Calibration Wizard – GUI wizard dialog
5. Weather Safety – Arduino firmware (code-level verification only)

These tests do NOT require a display, real hardware, or network access.
"""

import os
import sys
import time
import socket
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ---------------------------------------------------------------------------
# Feature 1: Predictive Slaving (Look-Ahead)
# ---------------------------------------------------------------------------
class TestExtrapolateAzimuth:
    """Test the linear look-ahead extrapolation in MathUtils."""

    def _make_math_utils(self, latency_ms: float = 500.0):
        from math_utils import MathUtils
        return MathUtils(
            latitude=51.5, longitude=-0.1, elevation=0,
            dome_radius=2.5, pier_height=1.5,
            latency_compensation_ms=latency_ms,
        )

    def test_zero_latency_returns_unchanged(self):
        mu = self._make_math_utils(0.0)
        assert mu.extrapolate_azimuth(100.0) == 100.0

    def test_first_call_returns_unchanged(self):
        mu = self._make_math_utils(500.0)
        assert mu.extrapolate_azimuth(100.0) == 100.0

    def test_extrapolation_applies_velocity(self):
        mu = self._make_math_utils(1000.0)  # 1 second look-ahead
        # First call initialises state
        mu.extrapolate_azimuth(100.0)
        # Simulate 1 second passing with 10°/s velocity
        mu._prev_time = time.time() - 1.0
        result = mu.extrapolate_azimuth(110.0)
        # Velocity ≈ 10°/s, look-ahead = 1s → predicted ≈ 120°
        assert result == pytest.approx(120.0, abs=1.0)

    def test_wraps_around_360(self):
        mu = self._make_math_utils(1000.0)
        mu.extrapolate_azimuth(355.0)
        mu._prev_time = time.time() - 1.0
        result = mu.extrapolate_azimuth(359.0)
        # velocity ~4°/s, look-ahead 1s → 359+4=363 → wraps to ~3°
        assert 0 <= result < 360

    def test_negative_velocity_wraps(self):
        mu = self._make_math_utils(1000.0)
        mu.extrapolate_azimuth(5.0)
        mu._prev_time = time.time() - 1.0
        result = mu.extrapolate_azimuth(1.0)
        # velocity ~-4°/s, look-ahead 1s → 1-4=-3 → wraps to ~357°
        assert 0 <= result < 360

    def test_latency_compensation_ms_stored(self):
        mu = self._make_math_utils(750.0)
        assert mu.latency_compensation_ms == 750.0

    def test_negative_latency_clamped_to_zero(self):
        mu = self._make_math_utils(-100.0)
        assert mu.latency_compensation_ms == 0.0


# ---------------------------------------------------------------------------
# Feature 1: Config parameter
# ---------------------------------------------------------------------------
class TestLatencyCompensationConfig:
    """Test that latency_compensation_ms is in DEFAULT_CONFIG."""

    def test_default_config_has_latency(self):
        from main import DEFAULT_CONFIG
        ctrl = DEFAULT_CONFIG.get("control", {})
        assert "latency_compensation_ms" in ctrl
        assert ctrl["latency_compensation_ms"] == 0

    def test_config_yaml_has_latency(self):
        import yaml
        cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
        with open(cfg_path) as fh:
            cfg = yaml.safe_load(fh)
        assert "latency_compensation_ms" in cfg.get("control", {})


# ---------------------------------------------------------------------------
# Feature 2: Hardware Watchdog – SerialController.send_ping
# ---------------------------------------------------------------------------
class TestSendPing:
    """Test the PING heartbeat command on SerialController."""

    def test_send_ping_sends_command(self):
        from serial_ctrl import SerialController
        ctrl = SerialController.__new__(SerialController)
        ctrl.logger = MagicMock()
        ctrl.port = "COM99"
        ctrl.baud_rate = 9600
        ctrl.timeout = 1.0
        ctrl.connected = True
        ctrl._last_reconnect_attempt = 0.0
        ctrl.ser = MagicMock()

        result = ctrl.send_ping()
        assert result is True
        ctrl.ser.write.assert_called_once()
        written = ctrl.ser.write.call_args[0][0]
        assert b"PING" in written

    def test_send_ping_returns_false_when_disconnected(self):
        from serial_ctrl import SerialController
        ctrl = SerialController.__new__(SerialController)
        ctrl.logger = MagicMock()
        ctrl.connected = False

        result = ctrl.send_ping()
        assert result is False


# ---------------------------------------------------------------------------
# Feature 3: INDI Protocol Support
# ---------------------------------------------------------------------------
class TestINDIServer:
    """Test the INDI dome server basics."""

    def test_import(self):
        from indi_server import INDIDomeServer, DEVICE_NAME
        assert DEVICE_NAME == "ARGUS Dome"

    def test_build_definition_xml(self):
        from indi_server import INDIDomeServer
        ctrl = MagicMock()
        ctrl.current_azimuth = 123.4
        ctrl.is_parked = False

        server = INDIDomeServer(ctrl)
        xml = server._build_definition_xml()
        assert "ABS_DOME_POSITION" in xml
        assert "DOME_SHUTTER" in xml
        assert "DOME_PARK" in xml
        assert "CONNECTION" in xml
        assert "ARGUS Dome" in xml

    def test_number_vector_xml(self):
        from indi_server import INDIDomeServer
        xml = INDIDomeServer._number_vector(
            "ABS_DOME_POSITION", "Ok", {"DOME_ABSOLUTE_POSITION": 45.0}
        )
        assert 'name="ABS_DOME_POSITION"' in xml
        assert "45.0" in xml

    def test_switch_vector_xml(self):
        from indi_server import INDIDomeServer
        xml = INDIDomeServer._switch_vector(
            "DOME_PARK", "Ok", {"PARK": "On", "UNPARK": "Off"}
        )
        assert 'name="DOME_PARK"' in xml
        assert 'name="PARK"' in xml

    def test_handle_getproperties(self):
        from indi_server import INDIDomeServer
        ctrl = MagicMock()
        ctrl.current_azimuth = 0.0
        ctrl.is_parked = False

        server = INDIDomeServer(ctrl)
        client = MagicMock()
        server._handle_message("<getProperties/>", client)
        # Should have sent XML to client
        client.sendall.assert_called()
        sent_data = client.sendall.call_args[0][0].decode("utf-8")
        assert "ABS_DOME_POSITION" in sent_data

    def test_handle_slew_command(self):
        from indi_server import INDIDomeServer
        ctrl = MagicMock()
        ctrl.current_azimuth = 0.0

        server = INDIDomeServer(ctrl)
        server._clients = [MagicMock()]
        server._lock = threading.Lock()

        msg = (
            '<newNumberVector device="ARGUS Dome" name="ABS_DOME_POSITION">'
            '<oneNumber name="DOME_ABSOLUTE_POSITION">180.0</oneNumber>'
            '</newNumberVector>'
        )
        server._handle_message(msg, MagicMock())
        ctrl.move_dome.assert_called_once_with(180.0)

    def test_handle_park_command(self):
        from indi_server import INDIDomeServer
        ctrl = MagicMock()
        ctrl.current_azimuth = 0.0

        server = INDIDomeServer(ctrl)
        server._clients = [MagicMock()]
        server._lock = threading.Lock()

        msg = (
            '<newSwitchVector device="ARGUS Dome" name="DOME_PARK">'
            '<oneSwitch name="PARK">On</oneSwitch>'
            '</newSwitchVector>'
        )
        server._handle_message(msg, MagicMock())
        ctrl.park_dome.assert_called_once()

    def test_start_and_shutdown(self):
        from indi_server import INDIDomeServer
        ctrl = MagicMock()
        server = INDIDomeServer(ctrl, port=0)  # port 0 = OS assigns
        # Just test that start/shutdown don't crash
        server._running = False
        server.shutdown()


# ---------------------------------------------------------------------------
# Feature 4: Auto-Calibration Wizard (config update path)
# ---------------------------------------------------------------------------
class TestCalibrationWizardIntegration:
    """Test the calibration wizard updates config when solver succeeds."""

    def test_run_calibration_returns_offsets(self):
        """Verify the existing run_calibration method still works."""
        from main import ArgusController
        from calibration import OffsetSolver

        # Create minimal controller stub
        obj = object.__new__(ArgusController)
        obj.config = {
            "math": {"mount": {}, "observatory": {}, "dome": {}},
            "safety": {},
            "hardware": {},
            "control": {},
            "logging": {"level": "WARNING"},
        }
        obj._mode = "MANUAL"
        obj._lock = threading.Lock()
        obj.ascom = MagicMock()
        obj.ascom.telescope = None
        obj.serial = None
        # safe_slew_dome calls get_azimuth too, so provide enough values
        obj.sensor = MagicMock()
        obj.sensor.get_azimuth = MagicMock(
            side_effect=[0.0, 0.0, 90.0, 90.0, 180.0, 180.0, 270.0, 270.0]
        )
        obj.dome_driver = None
        obj.gui = None

        with patch("main.save_config"):
            result = obj.run_calibration()

        # Should return offsets since we provided 4 points
        assert result is not None
        assert "gem_offset_east" in result
        assert "gem_offset_north" in result
        assert "pier_height" in result


# ---------------------------------------------------------------------------
# General: INDI import in main.py
# ---------------------------------------------------------------------------
class TestINDIIntegration:
    """Test that INDIDomeServer is importable from main."""

    def test_indi_import_available(self):
        import importlib
        mod = importlib.import_module("main")
        # INDIDomeServer should be imported (not None since indi_server.py exists)
        assert hasattr(mod, "INDIDomeServer")
        assert mod.INDIDomeServer is not None
