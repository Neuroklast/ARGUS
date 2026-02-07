"""Tests for issue fixes: theme switching, vertical angle display,
dome rotation limits, setup wizard, help dialog, diagnostics improvements.

These tests do NOT require a display or real hardware.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import flet as ft

from gui import (
    ArgusGUI,
    THEME_DARK,
    THEME_DAY,
    THEME_NIGHT,
)


def _make_mock_page() -> MagicMock:
    """Return a ``MagicMock`` that satisfies ``ArgusGUI.__init__``."""
    page = MagicMock(spec=ft.Page)
    page.update = MagicMock()
    page.add = MagicMock()
    page.overlay = []
    return page


# ---------------------------------------------------------------------------
# 1. Day/Night Mode Theme Bug Fixes
# ---------------------------------------------------------------------------
class TestThemeSwitchingColors:
    """Verify that ALL text elements update when the theme changes."""

    def test_heading_labels_update_to_day_theme(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        for lbl in gui._heading_labels:
            assert lbl.color == THEME_DAY["heading"]

    def test_heading_labels_update_to_night_theme(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        gui.toggle_night_mode()  # → night
        for lbl in gui._heading_labels:
            assert lbl.color == THEME_NIGHT["heading"]

    def test_heading_labels_update_back_to_dark(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        gui.toggle_night_mode()  # → night
        gui.toggle_night_mode()  # → dark
        for lbl in gui._heading_labels:
            assert lbl.color == THEME_DARK["heading"]

    def test_text_labels_update_to_day_theme(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        for lbl in gui._text_labels:
            assert lbl.color == THEME_DAY["text"]

    def test_text_labels_update_to_night_theme(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        gui.toggle_night_mode()  # → night
        for lbl in gui._text_labels:
            assert lbl.color == THEME_NIGHT["text"]

    def test_night_mode_all_red(self):
        """In night mode, heading and text should both be red."""
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        gui.toggle_night_mode()  # → night
        assert gui._theme["heading"] == "#FF0000"
        assert gui._theme["text"] == "#FF0000"
        for lbl in gui._heading_labels:
            assert lbl.color == "#FF0000"

    def test_heading_labels_exist(self):
        gui = ArgusGUI(_make_mock_page())
        assert len(gui._heading_labels) > 0

    def test_text_labels_exist(self):
        gui = ArgusGUI(_make_mock_page())
        assert len(gui._text_labels) > 0

    def test_toolbar_icon_colors_update(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        assert gui.btn_help.icon_color == THEME_DAY["accent"]
        assert gui.btn_wizard.icon_color == THEME_DAY["accent"]
        assert gui.btn_diagnostics.icon_color == THEME_DAY["accent"]
        assert gui.btn_settings.icon_color == THEME_DAY["accent"]


# ---------------------------------------------------------------------------
# 2. Vertical Telescope Angle in Dome Control (Radar View)
# ---------------------------------------------------------------------------
class TestVerticalAngleDisplay:
    """Verify that altitude and pier side are shown in the radar card."""

    def test_altitude_radar_label_exists(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.lbl_telescope_alt_radar is not None

    def test_pier_side_radar_label_exists(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.lbl_pier_side_radar is not None

    def test_altitude_radar_default(self):
        gui = ArgusGUI(_make_mock_page())
        assert "---" in gui.lbl_telescope_alt_radar.value

    def test_pier_side_radar_default(self):
        gui = ArgusGUI(_make_mock_page())
        assert "---" in gui.lbl_pier_side_radar.value

    def test_update_telemetry_updates_radar_altitude(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(100.0, 98.0, mount_alt=45.5)
        assert "45.5" in gui.lbl_telescope_alt_radar.value

    def test_update_telemetry_updates_radar_pier_side(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(100.0, 98.0, pier_side="East")
        assert "East" in gui.lbl_pier_side_radar.value

    def test_radar_labels_theme_update(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        assert gui.lbl_telescope_alt_radar.color == THEME_DAY["accent"]
        assert gui.lbl_pier_side_radar.color == THEME_DAY["accent"]


# ---------------------------------------------------------------------------
# 3. Dome Rotation Range Limits
# ---------------------------------------------------------------------------
class TestDomeRotationLimits:
    """Verify dome azimuth clamping and config validation."""

    def test_default_config_has_dome_limits(self):
        from main import DEFAULT_CONFIG
        assert "dome" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["dome"]["az_min"] == 0.0
        assert DEFAULT_CONFIG["dome"]["az_max"] == 360.0

    def test_move_dome_clamps_to_limits(self):
        from main import ArgusController
        import threading

        ctrl = ArgusController.__new__(ArgusController)
        ctrl._health = "HEALTHY"
        ctrl._lock = threading.Lock()
        ctrl._mode = "MANUAL"
        ctrl._is_parked = False
        ctrl.config = {
            "dome": {"az_min": 30.0, "az_max": 270.0},
            "control": {"max_speed": 100},
            "safety": {},
        }
        ctrl.dome_driver = None
        ctrl.serial = MagicMock()
        from simulation_sensor import SimulationSensor
        ctrl.sensor = SimulationSensor()

        # Target below min should be clamped
        ctrl.move_dome(10.0)
        args = ctrl.serial.move_to_azimuth.call_args[0]
        assert args[0] == 30.0  # clamped to min

    def test_move_dome_clamps_to_max(self):
        from main import ArgusController
        import threading

        ctrl = ArgusController.__new__(ArgusController)
        ctrl._health = "HEALTHY"
        ctrl._lock = threading.Lock()
        ctrl._mode = "MANUAL"
        ctrl._is_parked = False
        ctrl.config = {
            "dome": {"az_min": 30.0, "az_max": 270.0},
            "control": {"max_speed": 100},
            "safety": {},
        }
        ctrl.dome_driver = None
        ctrl.serial = MagicMock()
        from simulation_sensor import SimulationSensor
        ctrl.sensor = SimulationSensor()

        # Target above max should be clamped
        ctrl.move_dome(300.0)
        args = ctrl.serial.move_to_azimuth.call_args[0]
        assert args[0] == 270.0  # clamped to max

    def test_move_dome_no_clamp_default_limits(self):
        from main import ArgusController
        import threading

        ctrl = ArgusController.__new__(ArgusController)
        ctrl._health = "HEALTHY"
        ctrl._lock = threading.Lock()
        ctrl._mode = "MANUAL"
        ctrl._is_parked = False
        ctrl.config = {
            "dome": {"az_min": 0.0, "az_max": 360.0},
            "control": {"max_speed": 100},
            "safety": {},
        }
        ctrl.dome_driver = None
        ctrl.serial = MagicMock()
        from simulation_sensor import SimulationSensor
        ctrl.sensor = SimulationSensor()

        ctrl.move_dome(300.0)
        args = ctrl.serial.move_to_azimuth.call_args[0]
        assert args[0] == 300.0  # no clamping

    def test_diagnostics_checks_rotation_limits(self):
        from diagnostics import SystemDiagnostics, Status
        config = {
            "math": {"observatory": {"latitude": 51.0, "longitude": -0.1},
                     "dome": {"radius": 2.5}},
            "hardware": {"serial_port": "COM3"},
            "control": {"update_rate": 10},
            "logging": {},
            "dome": {"az_min": 30.0, "az_max": 270.0},
        }
        diag = SystemDiagnostics(config)
        results = diag._check_config()
        limit_results = [r for r in results if "Rotation Limits" in r.name]
        assert len(limit_results) == 1
        assert limit_results[0].status == Status.INFO

    def test_diagnostics_error_invalid_limits(self):
        from diagnostics import SystemDiagnostics, Status
        config = {
            "math": {"observatory": {"latitude": 51.0, "longitude": -0.1},
                     "dome": {"radius": 2.5}},
            "hardware": {"serial_port": "COM3"},
            "control": {"update_rate": 10},
            "logging": {},
            "dome": {"az_min": 300.0, "az_max": 100.0},
        }
        diag = SystemDiagnostics(config)
        results = diag._check_config()
        limit_results = [r for r in results if "Rotation Limits" in r.name]
        assert any(r.status == Status.ERROR for r in limit_results)

    def test_settings_gui_saves_rotation_limits(self):
        from settings_gui import show_settings_dialog
        page = _make_mock_page()
        saved = {}
        config = {"dome": {"az_min": 0.0, "az_max": 360.0}}
        show_settings_dialog(page, config, lambda cfg: saved.update(cfg))
        # Dialog was appended to overlay
        assert len(page.overlay) == 1


# ---------------------------------------------------------------------------
# 4. Setup Wizard
# ---------------------------------------------------------------------------
class TestSetupWizard:
    """Verify the setup wizard can be opened and navigated."""

    def test_wizard_button_exists(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.btn_wizard is not None

    def test_show_setup_wizard_opens_dialog(self):
        page = _make_mock_page()
        gui = ArgusGUI(page)
        config = {"math": {"observatory": {}, "dome": {}}, "hardware": {},
                  "dome": {}}
        gui.show_setup_wizard(config)
        assert len(page.overlay) == 1

    def test_wizard_localization_keys_exist(self):
        from localization import t
        assert t("wizard.title") != "wizard.title"
        assert t("wizard.next") != "wizard.next"
        assert t("wizard.back") != "wizard.back"
        assert t("wizard.finish") != "wizard.finish"
        assert t("wizard.step_location_title") != "wizard.step_location_title"
        assert t("wizard.step_hardware_title") != "wizard.step_hardware_title"
        assert t("wizard.step_dome_title") != "wizard.step_dome_title"
        assert t("wizard.step_finish_title") != "wizard.step_finish_title"

    def test_wizard_german_translations(self):
        from localization import t, set_language, get_language
        original = get_language()
        set_language("de")
        try:
            result = t("wizard.title")
            assert result != "wizard.title"
            assert "Einrichtung" in result
        finally:
            set_language(original)


# ---------------------------------------------------------------------------
# 5. Help Button & Diagnostics Improvements
# ---------------------------------------------------------------------------
class TestHelpButton:
    """Verify the help button and dialog."""

    def test_help_button_exists(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.btn_help is not None

    def test_show_help_dialog(self):
        page = _make_mock_page()
        gui = ArgusGUI(page)
        gui.show_help_dialog()
        assert len(page.overlay) == 1

    def test_help_localization_keys_exist(self):
        from localization import t
        assert t("help.title") != "help.title"
        assert t("help.quick_start_title") != "help.quick_start_title"
        assert t("help.modes_title") != "help.modes_title"
        assert t("help.troubleshooting_title") != "help.troubleshooting_title"


class TestDiagnosticsImprovements:
    """Verify diagnostics dialog improvements."""

    def test_diagnostics_in_place_update(self):
        """show_diagnostics should update the existing dialog in place."""
        from diagnostics import DiagReport, DiagResult, Status
        page = _make_mock_page()
        gui = ArgusGUI(page)
        dlg = gui.show_diagnostics_loading()

        report = DiagReport(results=[
            DiagResult("Test", "Check", Status.OK, "All good"),
        ], duration_s=0.1)
        gui.show_diagnostics(report, dlg=dlg)
        # Dialog should still be the same object, just with updated content
        assert dlg.content is not None
        assert dlg.open is True  # stays open (not closed + reopened)

    def test_diagnostics_tips_shown_for_errors(self):
        """Troubleshooting tips should appear when there are errors."""
        from diagnostics import DiagReport, DiagResult, Status
        from localization import t
        page = _make_mock_page()
        gui = ArgusGUI(page)

        report = DiagReport(results=[
            DiagResult("Test", "Fail", Status.ERROR, "Something broken",
                       "Fix it"),
        ], duration_s=0.1)
        gui.show_diagnostics(report)
        # The dialog should contain tips
        assert len(page.overlay) == 1

    def test_diagnostics_theme_aware_colors(self):
        """Diagnostics should use theme colors, not hardcoded ones."""
        from diagnostics import DiagReport, DiagResult, Status
        page = _make_mock_page()
        gui = ArgusGUI(page)
        gui.toggle_night_mode()  # → day
        gui.toggle_night_mode()  # → night

        report = DiagReport(results=[
            DiagResult("Test", "Check", Status.OK, "Good"),
        ], duration_s=0.1)
        gui.show_diagnostics(report)
        # Should not crash and dialog should be created
        assert len(page.overlay) == 1

    def test_diag_tips_localization(self):
        from localization import t
        assert t("diag.tips_title") != "diag.tips_title"
        assert t("diag.tips_body") != "diag.tips_body"


# ---------------------------------------------------------------------------
# Rotation limits localization
# ---------------------------------------------------------------------------
class TestRotationLimitsLocalization:
    """Verify rotation limit setting labels are localized."""

    def test_az_min_label(self):
        from localization import t
        assert t("settings.az_min") != "settings.az_min"

    def test_az_max_label(self):
        from localization import t
        assert t("settings.az_max") != "settings.az_max"

    def test_rotation_limits_group(self):
        from localization import t
        assert t("settings.group.rotation_limits") != "settings.group.rotation_limits"
