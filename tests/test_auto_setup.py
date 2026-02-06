"""Tests for newly added features: save_config, ASCOMHandler extensions,
VisionSystem.find_working_camera, OffsetSolver, safe_slew_dome, and
ArgusController auto-setup / sync helpers.

These tests do NOT require a display or real hardware.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import yaml

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import (
    DEFAULT_CONFIG,
    load_config,
    save_config,
)


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------
class TestSaveConfig:
    """Tests for the save_config helper."""

    def test_round_trip(self, tmp_path):
        """save_config → load_config should reproduce the data."""
        cfg = dict(DEFAULT_CONFIG)
        cfg_file = str(tmp_path / "out.yaml")
        save_config(cfg, cfg_file)
        loaded = load_config(cfg_file)
        assert loaded["ascom"]["telescope_prog_id"] == cfg["ascom"]["telescope_prog_id"]
        assert loaded["control"]["update_rate"] == cfg["control"]["update_rate"]

    def test_creates_file(self, tmp_path):
        """save_config should create a new file."""
        cfg_file = tmp_path / "new.yaml"
        save_config({"hello": "world"}, str(cfg_file))
        assert cfg_file.exists()
        data = yaml.safe_load(cfg_file.read_text())
        assert data["hello"] == "world"

    def test_overwrites_existing(self, tmp_path):
        """save_config should overwrite an existing file."""
        cfg_file = tmp_path / "cfg.yaml"
        cfg_file.write_text("old: data\n")
        save_config({"new": "data"}, str(cfg_file))
        data = yaml.safe_load(cfg_file.read_text())
        assert "new" in data
        assert "old" not in data

    def test_invalid_path_logs_error(self, tmp_path):
        """save_config with an unwritable path should not raise."""
        # /dev/null/impossible is not writable
        save_config({"a": 1}, "/dev/null/impossible/cfg.yaml")

    def test_safety_section_in_default(self):
        """DEFAULT_CONFIG should contain the safety section."""
        assert "safety" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["safety"]["telescope_protrudes"] is True
        assert DEFAULT_CONFIG["safety"]["safe_altitude"] == 90.0
        assert DEFAULT_CONFIG["safety"]["max_nudge_while_protruding"] == 2.0


# ---------------------------------------------------------------------------
# ASCOMHandler extensions
# ---------------------------------------------------------------------------
class TestASCOMHandlerExtensions:
    """Tests for get_site_data and choose_device (mocked)."""

    def _make_handler(self):
        """Create a minimal ASCOMHandler stub without win32com."""
        from ascom_handler import ASCOMHandler

        obj = object.__new__(ASCOMHandler)
        obj.logger = MagicMock()
        obj.prog_id = "Test.Telescope"
        obj.telescope = MagicMock()
        obj.connected = True
        obj._last_reconnect_attempt = 0.0
        return obj

    def test_get_site_data_returns_coords(self):
        handler = self._make_handler()
        handler.telescope.SiteLatitude = 48.1
        handler.telescope.SiteLongitude = 11.5
        handler.telescope.SiteElevation = 520.0
        result = handler.get_site_data()
        assert result == {"latitude": 48.1, "longitude": 11.5, "elevation": 520.0}

    def test_get_site_data_elevation_fallback(self):
        handler = self._make_handler()
        handler.telescope.SiteLatitude = 48.1
        handler.telescope.SiteLongitude = 11.5
        type(handler.telescope).SiteElevation = PropertyMock(side_effect=Exception("unsupported"))
        result = handler.get_site_data()
        assert result is not None
        assert result["elevation"] == 0.0

    def test_get_site_data_not_connected(self):
        handler = self._make_handler()
        handler.connected = False
        assert handler.get_site_data() is None

    def test_choose_device_no_win32com(self):
        """choose_device returns None when ASCOM is unavailable."""
        from ascom_handler import ASCOMHandler
        with patch("ascom_handler.ASCOM_AVAILABLE", False):
            assert ASCOMHandler.choose_device("test") is None


# ---------------------------------------------------------------------------
# VisionSystem.find_working_camera
# ---------------------------------------------------------------------------
class TestFindWorkingCamera:
    """Tests for VisionSystem.find_working_camera (cv2 mocked)."""

    def test_no_cameras(self):
        from vision import VisionSystem

        with patch("cv2.VideoCapture") as mock_cap:
            cap_instance = MagicMock()
            cap_instance.isOpened.return_value = False
            mock_cap.return_value = cap_instance

            result = VisionSystem.find_working_camera(max_indices=3)
            assert result is None

    def test_first_camera_works(self):
        from vision import VisionSystem

        with patch("cv2.VideoCapture") as mock_cap:
            cap_instance = MagicMock()
            cap_instance.isOpened.return_value = True
            cap_instance.read.return_value = (True, MagicMock())
            mock_cap.return_value = cap_instance

            with patch("cv2.cvtColor") as mock_cvt:
                mock_cvt.return_value = MagicMock()
                with patch("cv2.aruco.ArucoDetector") as mock_det:
                    det_instance = MagicMock()
                    det_instance.detectMarkers.return_value = ([], None, [])
                    mock_det.return_value = det_instance

                    result = VisionSystem.find_working_camera(max_indices=2)
                    assert result == 0

    def test_prefers_aruco_camera(self):
        from vision import VisionSystem
        import numpy as np

        call_count = [0]

        def make_cap(idx):
            cap = MagicMock()
            cap.isOpened.return_value = True
            cap.read.return_value = (True, np.zeros((100, 100, 3), dtype=np.uint8))
            return cap

        with patch("cv2.VideoCapture", side_effect=make_cap):
            with patch("cv2.cvtColor", return_value=MagicMock()):
                with patch("cv2.aruco.ArucoDetector") as mock_det:
                    det = MagicMock()

                    def detect_side(gray):
                        nonlocal call_count
                        call_count[0] += 1
                        if call_count[0] == 2:
                            # Second camera has a marker
                            return ([MagicMock()], np.array([[1]]), [])
                        return ([], None, [])

                    det.detectMarkers = detect_side
                    mock_det.return_value = det

                    result = VisionSystem.find_working_camera(max_indices=3)
                    assert result == 1  # preferred because it has ArUco


# ---------------------------------------------------------------------------
# OffsetSolver
# ---------------------------------------------------------------------------
class TestOffsetSolver:
    """Tests for the calibration OffsetSolver."""

    def test_too_few_points_returns_none(self):
        from calibration import OffsetSolver

        solver = OffsetSolver()
        solver.add_point(90, 45, 90)
        solver.add_point(180, 45, 180)
        assert solver.solve() is None

    def test_solve_identity(self):
        """With zero offsets, predicted == observed → offsets ≈ 0."""
        from calibration import OffsetSolver

        solver = OffsetSolver()
        for az in (0, 90, 180, 270):
            # When offsets are zero, predicted dome az ≈ telescope az
            predicted = OffsetSolver._predicted_dome_az(az, 45, 0.0, 0.0, 1.5)
            solver.add_point(az, 45, predicted)

        result = solver.solve()
        assert result is not None
        assert abs(result["gem_offset_east"]) < 0.1
        assert abs(result["gem_offset_north"]) < 0.1

    def test_solve_returns_all_keys(self):
        from calibration import OffsetSolver

        solver = OffsetSolver()
        for az in (0, 90, 180, 270):
            solver.add_point(az, 45, az + 1.0)
        result = solver.solve()
        assert result is not None
        assert "gem_offset_east" in result
        assert "gem_offset_north" in result
        assert "pier_height" in result

    def test_predicted_dome_az_basic(self):
        from calibration import OffsetSolver

        az = OffsetSolver._predicted_dome_az(90, 45, 0.0, 0.0, 1.5)
        assert 0 <= az < 360


# ---------------------------------------------------------------------------
# safe_slew_dome (unit-level)
# ---------------------------------------------------------------------------
class TestSafeSlew:
    """Test safe_slew_dome logic without GUI."""

    def _make_controller_stub(self):
        from main import ArgusController

        obj = object.__new__(ArgusController)
        obj._health = "HEALTHY"
        obj._lock = __import__("threading").Lock()
        obj._mode = "MANUAL"
        obj.config = dict(DEFAULT_CONFIG)
        obj.ascom = None
        obj.serial = None
        obj.vision = None
        obj.math_utils = None
        obj.sensor = MagicMock()
        obj.sensor.get_azimuth.return_value = 100.0
        return obj

    def test_direct_slew_when_not_protruding(self):
        c = self._make_controller_stub()
        c.config["safety"]["telescope_protrudes"] = False
        c.serial = MagicMock()
        c.safe_slew_dome(110.0)
        c.serial.move_to_azimuth.assert_called_once()

    def test_direct_slew_when_small_delta(self):
        c = self._make_controller_stub()
        c.config["safety"]["telescope_protrudes"] = True
        c.config["safety"]["max_nudge_while_protruding"] = 5.0
        c.sensor.get_azimuth.return_value = 100.0
        c.serial = MagicMock()
        c.safe_slew_dome(103.0)  # delta = 3 < 5
        c.serial.move_to_azimuth.assert_called_once()

    def test_retract_slew_when_large_delta(self):
        c = self._make_controller_stub()
        c.config["safety"]["telescope_protrudes"] = True
        c.config["safety"]["max_nudge_while_protruding"] = 2.0
        c.sensor.get_azimuth.return_value = 100.0
        c.ascom = MagicMock()
        telescope = MagicMock()
        telescope.Slewing = False
        c.ascom.telescope = telescope
        c.serial = MagicMock()
        c.safe_slew_dome(200.0)  # delta = 100 > 2
        telescope.SlewToAltAz.assert_called_once()
        c.serial.move_to_azimuth.assert_called_once()


# ---------------------------------------------------------------------------
# _sync_site_data (unit-level)
# ---------------------------------------------------------------------------
class TestSyncSiteData:
    """Test _sync_site_data helper."""

    def _make_controller_stub(self):
        from main import ArgusController

        obj = object.__new__(ArgusController)
        obj._health = "HEALTHY"
        obj._lock = __import__("threading").Lock()
        obj.config = {
            "math": {"observatory": {"latitude": 0.0, "longitude": 0.0, "elevation": 0}},
            "ascom": {"telescope_prog_id": "Test"},
            "vision": {},
            "hardware": {},
            "control": {},
            "logging": {},
            "safety": {},
        }
        obj.ascom = MagicMock()
        obj.serial = None
        obj.vision = None
        obj.math_utils = None
        return obj

    def test_sync_updates_config(self, tmp_path):
        c = self._make_controller_stub()
        c.ascom.get_site_data.return_value = {
            "latitude": 48.1,
            "longitude": 11.5,
            "elevation": 520.0,
        }
        cfg_file = str(tmp_path / "cfg.yaml")
        save_config(c.config, cfg_file)

        with patch("main.save_config") as mock_save:
            c._sync_site_data()
            mock_save.assert_called_once()

        obs = c.config["math"]["observatory"]
        assert obs["latitude"] == 48.1
        assert obs["longitude"] == 11.5
        assert obs["elevation"] == 520.0

    def test_sync_noop_when_same(self):
        c = self._make_controller_stub()
        c.config["math"]["observatory"] = {
            "latitude": 48.1,
            "longitude": 11.5,
            "elevation": 520.0,
        }
        c.ascom.get_site_data.return_value = {
            "latitude": 48.1,
            "longitude": 11.5,
            "elevation": 520.0,
        }
        with patch("main.save_config") as mock_save:
            c._sync_site_data()
            mock_save.assert_not_called()
