"""Tests for new features: config validation, health states, drift filter,
normalize_azimuth, settings_gui, serial reconnect, ASCOM reconnect.

These tests do NOT require a display or real hardware.
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import (
    DEFAULT_CONFIG,
    HEALTH_CRITICAL,
    HEALTH_DEGRADED,
    HEALTH_HEALTHY,
    _deep_merge,
    _type_ok,
    load_config,
    normalize_azimuth,
)


# ---------------------------------------------------------------------------
# normalize_azimuth
# ---------------------------------------------------------------------------
class TestNormalizeAzimuth:
    def test_normal_value(self):
        assert normalize_azimuth(90.0) == 90.0

    def test_wraps_above_360(self):
        assert normalize_azimuth(400.0) == pytest.approx(40.0)

    def test_negative(self):
        assert normalize_azimuth(-10.0) == pytest.approx(350.0)

    def test_zero(self):
        assert normalize_azimuth(0.0) == 0.0

    def test_exactly_360(self):
        assert normalize_azimuth(360.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _type_ok helper
# ---------------------------------------------------------------------------
class TestTypeOk:
    def test_int_accepts_int(self):
        assert _type_ok(1, 2) is True

    def test_int_accepts_float(self):
        assert _type_ok(1, 2.5) is True

    def test_float_accepts_int(self):
        assert _type_ok(1.0, 2) is True

    def test_str_rejects_int(self):
        assert _type_ok("hello", 42) is False

    def test_bool_rejects_int(self):
        assert _type_ok(True, 1) is False

    def test_bool_accepts_bool(self):
        assert _type_ok(True, False) is True


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------
class TestDeepMerge:
    def test_override_simple(self):
        result = _deep_merge({"a": 1}, {"a": 2})
        assert result["a"] == 2

    def test_missing_key_uses_default(self):
        result = _deep_merge({"a": 1, "b": 2}, {"a": 10})
        assert result["b"] == 2

    def test_nested_merge(self):
        defaults = {"sec": {"x": 1, "y": 2}}
        overrides = {"sec": {"x": 99}}
        result = _deep_merge(defaults, overrides)
        assert result["sec"]["x"] == 99
        assert result["sec"]["y"] == 2

    def test_wrong_type_uses_default(self):
        result = _deep_merge({"port": "COM3"}, {"port": 123})
        assert result["port"] == "COM3"

    def test_extra_keys_preserved(self):
        result = _deep_merge({"a": 1}, {"a": 1, "extra": "foo"})
        assert result["extra"] == "foo"


# ---------------------------------------------------------------------------
# load_config with type validation
# ---------------------------------------------------------------------------
class TestLoadConfigValidation:
    def test_wrong_type_value_falls_back(self, tmp_path):
        cfg_file = tmp_path / "cfg.yaml"
        cfg_file.write_text("hardware:\n  baud_rate: 'not_a_number'\n")
        result = load_config(str(cfg_file))
        # baud_rate in DEFAULT_CONFIG is int 9600
        assert result["hardware"]["baud_rate"] == 9600

    def test_valid_override_accepted(self, tmp_path):
        cfg_file = tmp_path / "cfg.yaml"
        cfg_file.write_text("hardware:\n  baud_rate: 115200\n")
        result = load_config(str(cfg_file))
        assert result["hardware"]["baud_rate"] == 115200


# ---------------------------------------------------------------------------
# Drift filter
# ---------------------------------------------------------------------------
class TestDriftFilter:
    """Test the outlier rejection logic in ArgusController._filter_drift."""

    def _make_filter(self):
        """Create a minimal object with just the _filter_drift state."""
        from main import ArgusController

        obj = object.__new__(ArgusController)
        obj._last_drift_az = None
        obj._stable_drift_count = 0
        obj._pending_drift_az = None
        return obj

    def test_first_value_accepted(self):
        f = self._make_filter()
        assert f._filter_drift(100.0) == 100.0

    def test_small_change_accepted(self):
        f = self._make_filter()
        f._filter_drift(100.0)
        assert f._filter_drift(102.0) == 102.0

    def test_large_jump_rejected(self):
        f = self._make_filter()
        f._filter_drift(100.0)
        # Jump of 20° should be rejected
        assert f._filter_drift(120.0) is None

    def test_stable_after_3_frames(self):
        f = self._make_filter()
        f._filter_drift(100.0)
        # 3 stable frames at 120°
        assert f._filter_drift(120.0) is None
        assert f._filter_drift(120.0) is None
        assert f._filter_drift(120.0) == 120.0


# ---------------------------------------------------------------------------
# Health check (unit-level without GUI)
# ---------------------------------------------------------------------------
class TestHealthCheck:
    """Test check_system_health without creating a real GUI."""

    def _make_controller_stub(self):
        """Create a stub with just the attributes needed by check_system_health."""
        from main import ArgusController

        obj = object.__new__(ArgusController)
        obj._health = HEALTH_HEALTHY
        obj._lock = __import__("threading").Lock()
        obj.ascom = None
        obj.serial = None
        obj.vision = None
        return obj

    def test_all_none_is_critical(self):
        c = self._make_controller_stub()
        assert c.check_system_health() == HEALTH_CRITICAL

    def test_ascom_serial_only_is_degraded(self):
        c = self._make_controller_stub()
        c.ascom = MagicMock(connected=True)
        c.serial = MagicMock(connected=True)
        assert c.check_system_health() == HEALTH_DEGRADED

    def test_all_connected_is_healthy(self):
        c = self._make_controller_stub()
        c.ascom = MagicMock(connected=True)
        c.serial = MagicMock(connected=True)
        c.vision = MagicMock(camera_open=True)
        assert c.check_system_health() == HEALTH_HEALTHY


# ---------------------------------------------------------------------------
# SerialController reconnect
# ---------------------------------------------------------------------------
class TestSerialReconnect:
    def test_send_command_sets_connected_false_on_serial_error(self):
        from serial_ctrl import SerialController
        import serial

        ctrl = SerialController.__new__(SerialController)
        ctrl.logger = MagicMock()
        ctrl.port = "COM99"
        ctrl.baud_rate = 9600
        ctrl.timeout = 1.0
        ctrl.connected = True
        ctrl._last_reconnect_attempt = 0.0
        ctrl.ser = MagicMock()
        ctrl.ser.write.side_effect = serial.SerialException("disconnected")

        # The reconnect will also fail since there's no real serial port
        with patch.object(ctrl, 'connect', return_value=False):
            result = ctrl.send_command("TEST")

        assert ctrl.connected is False
        assert result is False

    def test_attempt_reconnect_respects_backoff(self):
        from serial_ctrl import SerialController

        ctrl = SerialController.__new__(SerialController)
        ctrl.logger = MagicMock()
        ctrl.port = "COM99"
        ctrl.baud_rate = 9600
        ctrl.timeout = 1.0
        ctrl.connected = False
        ctrl.ser = None
        ctrl._last_reconnect_attempt = time.time()

        with patch.object(ctrl, 'connect', return_value=True) as mock_connect:
            result = ctrl._attempt_reconnect()

        assert result is False
        mock_connect.assert_not_called()


# ---------------------------------------------------------------------------
# Settings GUI (headless – test config save/load logic)
# ---------------------------------------------------------------------------
class TestSettingsGuiHelpers:
    def test_to_int_valid(self):
        from settings_gui import SettingsWindow
        assert SettingsWindow._to_int("42", 0) == 42

    def test_to_int_invalid(self):
        from settings_gui import SettingsWindow
        assert SettingsWindow._to_int("abc", 99) == 99

    def test_to_float_valid(self):
        from settings_gui import SettingsWindow
        assert SettingsWindow._to_float("3.14", 0.0) == pytest.approx(3.14)

    def test_to_float_invalid(self):
        from settings_gui import SettingsWindow
        assert SettingsWindow._to_float("xyz", 1.5) == 1.5
