"""Tests for GUI startup and interface functionality.

These tests verify that the ARGUS GUI can be instantiated correctly and
that all key interface components are present and functional.  They run
headless by using a mocked Flet ``Page`` object so no display is needed.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gui import (
    ArgusGUI,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_ERROR,
    COLOR_OFF,
    COLOR_ON,
    COLOR_MOVING,
    COLOR_NO_SIGNAL,
    THEME_DARK,
    _card,
)

import flet as ft


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_page() -> MagicMock:
    """Return a ``MagicMock`` that satisfies ``ArgusGUI.__init__``."""
    page = MagicMock(spec=ft.Page)
    page.update = MagicMock()
    page.add = MagicMock()
    return page


# ---------------------------------------------------------------------------
# GUI instantiation
# ---------------------------------------------------------------------------
class TestGuiStartup:
    """Verify that the GUI can be constructed and all widgets are created."""

    def test_gui_instantiation(self):
        """ArgusGUI should construct without errors given a mock page."""
        page = _make_mock_page()
        gui = ArgusGUI(page)
        assert gui is not None

    def test_page_add_called(self):
        """_build_layout must call page.add() to mount the widget tree."""
        page = _make_mock_page()
        ArgusGUI(page)
        page.add.assert_called_once()

    def test_telemetry_labels_exist(self):
        """Mount AZ, Dome AZ, and Error labels must be present."""
        gui = ArgusGUI(_make_mock_page())
        assert gui.lbl_mount_az is not None
        assert gui.lbl_dome_az is not None
        assert gui.lbl_error is not None

    def test_telemetry_labels_initial_values(self):
        """Telemetry labels should show placeholder text at startup."""
        gui = ArgusGUI(_make_mock_page())
        assert "---" in gui.lbl_mount_az.value
        assert "---" in gui.lbl_dome_az.value
        assert "---" in gui.lbl_error.value

    def test_status_indicators_exist(self):
        """ASCOM, Vision, and Motor indicator badges must be created."""
        gui = ArgusGUI(_make_mock_page())
        assert gui.ind_ascom is not None
        assert gui.ind_vision is not None
        assert gui.ind_motor is not None

    def test_status_indicators_initial_off(self):
        """All status indicators should start in the OFF (grey) state."""
        gui = ArgusGUI(_make_mock_page())
        assert gui.ind_ascom.bgcolor == COLOR_OFF
        assert gui.ind_vision.bgcolor == COLOR_OFF
        assert gui.ind_motor.bgcolor == COLOR_OFF

    def test_control_buttons_exist(self):
        """CCW, STOP, and CW buttons must be present."""
        gui = ArgusGUI(_make_mock_page())
        assert gui.btn_ccw is not None
        assert gui.btn_stop is not None
        assert gui.btn_cw is not None

    def test_mode_selector_exists(self):
        """The mode SegmentedButton must be present."""
        gui = ArgusGUI(_make_mock_page())
        assert gui.mode_selector is not None

    def test_mode_selector_default_manual(self):
        """The default mode should be MANUAL."""
        gui = ArgusGUI(_make_mock_page())
        assert "MANUAL" in gui.mode_selector.selected

    def test_mode_selector_has_three_segments(self):
        """The mode selector must offer MANUAL, AUTO-SLAVE, CALIBRATE."""
        gui = ArgusGUI(_make_mock_page())
        values = [seg.value for seg in gui.mode_selector.segments]
        assert "MANUAL" in values
        assert "AUTO-SLAVE" in values
        assert "CALIBRATE" in values

    def test_settings_button_exists(self):
        """The settings button must be present."""
        gui = ArgusGUI(_make_mock_page())
        assert gui.btn_settings is not None

    def test_radar_canvas_exists(self):
        """The radar canvas must be present."""
        gui = ArgusGUI(_make_mock_page())
        assert gui.radar_canvas is not None

    def test_log_list_exists(self):
        """The system log list must be present and initially empty."""
        gui = ArgusGUI(_make_mock_page())
        assert gui.log_list is not None
        assert len(gui.log_list.controls) == 0


# ---------------------------------------------------------------------------
# Telemetry updates
# ---------------------------------------------------------------------------
class TestTelemetryUpdate:
    """Verify that update_telemetry correctly changes label values."""

    def test_update_telemetry_sets_values(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(123.4, 120.0)
        assert "123.4" in gui.lbl_mount_az.value
        assert "120.0" in gui.lbl_dome_az.value

    def test_update_telemetry_error_calculation(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(100.0, 97.0)
        # Error should be +3.0
        assert "+003.0" in gui.lbl_error.value

    def test_update_telemetry_error_wrap_positive(self):
        """Error should normalise across the 0°/360° boundary (positive)."""
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(5.0, 355.0)
        # Difference is 5 - 355 = -350, normalised to +10
        assert "+010.0" in gui.lbl_error.value

    def test_update_telemetry_error_wrap_negative(self):
        """Error should normalise across the 0°/360° boundary (negative)."""
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(355.0, 5.0)
        # Difference is 355 - 5 = 350, normalised to -10
        assert "-010.0" in gui.lbl_error.value

    def test_update_telemetry_error_at_180_boundary(self):
        """Error at exactly 180° should be +180 (not flipped)."""
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(180.0, 0.0)
        # 180 - 0 = 180 → not > 180, so stays as +180
        assert "+180.0" in gui.lbl_error.value

    def test_update_telemetry_calls_page_update(self):
        page = _make_mock_page()
        gui = ArgusGUI(page)
        page.update.reset_mock()
        gui.update_telemetry(0.0, 0.0)
        gui.batch_update()
        page.update.assert_called()

    def test_update_telemetry_tolerates_page_error(self):
        """If page.update() raises, update_telemetry must not propagate."""
        page = _make_mock_page()
        gui = ArgusGUI(page)
        page.update.side_effect = RuntimeError("connection lost")
        # Should not raise
        gui.update_telemetry(10.0, 20.0)


# ---------------------------------------------------------------------------
# Status indicators
# ---------------------------------------------------------------------------
class TestStatusIndicators:
    """Verify set_status / set_indicator behaviour."""

    def test_set_ascom_on(self):
        gui = ArgusGUI(_make_mock_page())
        gui.set_status("ascom", True)
        assert gui.ind_ascom.bgcolor == COLOR_ON

    def test_set_ascom_off(self):
        gui = ArgusGUI(_make_mock_page())
        gui.set_status("ascom", True)
        gui.set_status("ascom", False)
        assert gui.ind_ascom.bgcolor == COLOR_OFF

    def test_set_vision_on(self):
        gui = ArgusGUI(_make_mock_page())
        gui.set_status("vision", True)
        assert gui.ind_vision.bgcolor == COLOR_ON

    def test_set_motor_on_uses_moving_colour(self):
        gui = ArgusGUI(_make_mock_page())
        gui.set_status("motor", True)
        assert gui.ind_motor.bgcolor == COLOR_MOVING

    def test_set_unknown_component_ignored(self):
        gui = ArgusGUI(_make_mock_page())
        # Should not raise
        gui.set_status("unknown_component", True)

    def test_set_indicator_alias(self):
        """set_indicator should be an alias for set_status."""
        gui = ArgusGUI(_make_mock_page())
        gui.set_indicator("ascom", True)
        assert gui.ind_ascom.bgcolor == COLOR_ON


# ---------------------------------------------------------------------------
# System log
# ---------------------------------------------------------------------------
class TestSystemLog:
    """Verify write_log / append_log behaviour."""

    def test_write_log_adds_entry(self):
        gui = ArgusGUI(_make_mock_page())
        gui.write_log("Test message")
        assert len(gui.log_list.controls) == 1

    def test_write_log_contains_message(self):
        gui = ArgusGUI(_make_mock_page())
        gui.write_log("Hello ARGUS")
        text_value = gui.log_list.controls[0].value
        assert "Hello ARGUS" in text_value

    def test_write_log_contains_timestamp(self):
        gui = ArgusGUI(_make_mock_page())
        gui.write_log("timestamped")
        text_value = gui.log_list.controls[0].value
        # Timestamp format is [HH:MM:SS]
        assert "[" in text_value and "]" in text_value

    def test_append_log_alias(self):
        """append_log should be a backward-compatible alias for write_log."""
        gui = ArgusGUI(_make_mock_page())
        gui.append_log("via alias")
        assert len(gui.log_list.controls) == 1
        assert "via alias" in gui.log_list.controls[0].value

    def test_log_caps_at_200_entries(self):
        gui = ArgusGUI(_make_mock_page())
        for i in range(210):
            gui.write_log(f"message {i}")
        assert len(gui.log_list.controls) == 200

    def test_write_log_tolerates_page_error(self):
        page = _make_mock_page()
        gui = ArgusGUI(page)
        page.update.side_effect = RuntimeError("connection lost")
        # Should not raise
        gui.write_log("safe message")


# ---------------------------------------------------------------------------
# Radar
# ---------------------------------------------------------------------------
class TestRadar:
    """Verify radar drawing helpers."""

    def test_radar_shapes_returns_list(self):
        shapes = ArgusGUI._radar_shapes(0.0, 0.0)
        assert isinstance(shapes, list)
        assert len(shapes) > 0

    def test_radar_shapes_count(self):
        """The enriched radar should have grid rings, cross-hairs, labels,
        dome outline, mount line, arrowhead, slit arc, and pier marker."""
        shapes = ArgusGUI._radar_shapes(45.0, 90.0)
        # 3 rings + 2 cross-hairs + 4 labels + dome outline + mount line +
        # arrowhead + slit arc + pier marker = 14
        assert len(shapes) >= 10

    def test_draw_radar_updates_canvas(self):
        gui = ArgusGUI(_make_mock_page())
        gui.draw_radar(180.0, 270.0)
        assert len(gui.radar_canvas.shapes) >= 10


# ---------------------------------------------------------------------------
# Card helper
# ---------------------------------------------------------------------------
class TestCardHelper:
    """Verify the _card wrapper function."""

    def test_card_returns_container(self):
        content = ft.Text("test")
        container = _card(content)
        assert isinstance(container, ft.Container)

    def test_card_uses_correct_bg(self):
        container = _card(ft.Text("test"))
        assert container.bgcolor == COLOR_CARD_BG


# ---------------------------------------------------------------------------
# Session garbage-collection prevention
# ---------------------------------------------------------------------------
class TestSessionGcPrevention:
    """Verify that entry points pin objects on the page to prevent GC."""

    def test_standalone_main_stores_gui_on_page(self):
        """_standalone_main must store the GUI on the page to prevent GC."""
        from gui import _standalone_main

        page = _make_mock_page()
        page.window = MagicMock()
        _standalone_main(page)
        assert hasattr(page, "_argus_gui")
        assert isinstance(page._argus_gui, ArgusGUI)


# ---------------------------------------------------------------------------
# Status hints
# ---------------------------------------------------------------------------
class TestStatusHints:
    """Verify the set_status_hint method and hint label widgets."""

    def test_hint_labels_exist(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.hint_ascom is not None
        assert gui.hint_vision is not None
        assert gui.hint_motor is not None

    def test_hint_labels_initial_value(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.hint_ascom.value == "Not connected"
        assert gui.hint_vision.value == "Not connected"
        assert gui.hint_motor.value == "Not connected"

    def test_set_status_hint_updates_text(self):
        gui = ArgusGUI(_make_mock_page())
        gui.set_status_hint("ascom", "Connected")
        assert gui.hint_ascom.value == "Connected"

    def test_set_status_hint_unknown_component(self):
        gui = ArgusGUI(_make_mock_page())
        # Should not raise
        gui.set_status_hint("unknown", "test")

    def test_set_status_hint_tolerates_page_error(self):
        page = _make_mock_page()
        gui = ArgusGUI(page)
        page.update.side_effect = RuntimeError("gone")
        gui.set_status_hint("motor", "Reconnecting…")
        assert gui.hint_motor.value == "Reconnecting…"


# ---------------------------------------------------------------------------
# Connection banner
# ---------------------------------------------------------------------------
class TestConnectionBanner:
    """Verify the connection status banner."""

    def test_banner_exists(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.connection_banner is not None

    def test_banner_visible_initially(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.connection_banner.visible is True

    def test_banner_hidden_when_all_connected(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_connection_banner(True, True, True)
        assert gui.connection_banner.visible is False

    def test_banner_visible_when_partial(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_connection_banner(True, False, True)
        assert gui.connection_banner.visible is True
        text = gui.connection_banner.content.value
        assert "Camera" in text

    def test_banner_red_when_nothing_connected(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_connection_banner(False, False, False)
        assert gui.connection_banner.bgcolor == "#C0392B"
        assert "simulation" in gui.connection_banner.content.value.lower()

    def test_banner_yellow_when_partial(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_connection_banner(True, True, False)
        assert gui.connection_banner.bgcolor == "#F1C40F"

    def test_banner_lists_missing_components(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_connection_banner(False, True, False)
        text = gui.connection_banner.content.value
        assert "Telescope" in text
        assert "Motor" in text
        assert "Camera" not in text

    def test_banner_tolerates_page_error(self):
        page = _make_mock_page()
        gui = ArgusGUI(page)
        page.update.side_effect = RuntimeError("gone")
        gui.update_connection_banner(False, False, False)


# ---------------------------------------------------------------------------
# Diagnostics button
# ---------------------------------------------------------------------------
class TestDiagnosticsButton:
    """Verify the diagnostics button exists in the GUI."""

    def test_diagnostics_button_exists(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.btn_diagnostics is not None


# ---------------------------------------------------------------------------
# Diagnostics module
# ---------------------------------------------------------------------------
class TestDiagnostics:
    """Verify the diagnostics engine produces structured results."""

    def test_run_all_returns_report(self):
        from diagnostics import SystemDiagnostics, DiagReport
        from main import DEFAULT_CONFIG
        diag = SystemDiagnostics(dict(DEFAULT_CONFIG))
        report = diag.run_all()
        assert isinstance(report, DiagReport)
        assert len(report.results) > 0

    def test_report_has_summary(self):
        from diagnostics import SystemDiagnostics
        from main import DEFAULT_CONFIG
        diag = SystemDiagnostics(dict(DEFAULT_CONFIG))
        report = diag.run_all()
        assert isinstance(report.summary, str)
        assert len(report.summary) > 0

    def test_report_has_timestamp(self):
        from diagnostics import SystemDiagnostics
        from main import DEFAULT_CONFIG
        diag = SystemDiagnostics(dict(DEFAULT_CONFIG))
        report = diag.run_all()
        assert report.timestamp != ""

    def test_report_duration_positive(self):
        from diagnostics import SystemDiagnostics
        from main import DEFAULT_CONFIG
        diag = SystemDiagnostics(dict(DEFAULT_CONFIG))
        report = diag.run_all()
        assert report.duration_s >= 0

    def test_check_python_finds_flet(self):
        from diagnostics import SystemDiagnostics, Status
        from main import DEFAULT_CONFIG
        diag = SystemDiagnostics(dict(DEFAULT_CONFIG))
        results = diag._check_python()
        flet_result = [r for r in results if "flet" in r.name.lower()]
        assert len(flet_result) == 1
        assert flet_result[0].status == Status.OK

    def test_check_config_validates_location(self):
        from diagnostics import SystemDiagnostics, Status
        config = {"math": {"observatory": {"latitude": 0.0, "longitude": 0.0},
                           "dome": {"radius": 2.5}},
                  "hardware": {"serial_port": "COM3"},
                  "control": {"update_rate": 10},
                  "logging": {}}
        diag = SystemDiagnostics(config)
        results = diag._check_config()
        loc_results = [r for r in results if "Location" in r.name]
        assert any(r.status == Status.WARNING for r in loc_results)

    def test_check_config_invalid_rate(self):
        from diagnostics import SystemDiagnostics, Status
        config = {"math": {"observatory": {"latitude": 51.0, "longitude": -0.1},
                           "dome": {"radius": 2.5}},
                  "hardware": {"serial_port": "COM3"},
                  "control": {"update_rate": 0},
                  "logging": {}}
        diag = SystemDiagnostics(config)
        results = diag._check_config()
        rate_results = [r for r in results if "Update Rate" in r.name]
        assert any(r.status == Status.ERROR for r in rate_results)

    def test_diag_result_fields(self):
        from diagnostics import DiagResult, Status
        r = DiagResult(
            category="Test", name="Test Check",
            status=Status.OK, message="All good",
            suggestion="",
        )
        assert r.category == "Test"
        assert r.status == Status.OK

    def test_report_error_count(self):
        from diagnostics import DiagReport, DiagResult, Status
        report = DiagReport(results=[
            DiagResult("A", "a", Status.OK, "ok"),
            DiagResult("B", "b", Status.ERROR, "fail", "fix it"),
            DiagResult("C", "c", Status.WARNING, "warn"),
        ])
        assert len(report.errors) == 1
        assert len(report.warnings) == 1
        assert report.ok_count == 1


# ---------------------------------------------------------------------------
# Failsafe: emergency stop
# ---------------------------------------------------------------------------
class TestFailsafe:
    """Verify failsafe mechanisms in the controller."""

    def test_emergency_stop_stops_sensor(self):
        from main import ArgusController
        ctrl = ArgusController.__new__(ArgusController)
        ctrl._running = True
        ctrl.dome_driver = None
        ctrl.serial = None
        from simulation_sensor import SimulationSensor
        ctrl.sensor = SimulationSensor()
        ctrl.sensor.slew_rate = 5.0
        ctrl._emergency_stop()
        assert ctrl.sensor.slew_rate == 0.0
        assert ctrl._running is False

    def test_emergency_stop_calls_serial_stop(self):
        from main import ArgusController
        ctrl = ArgusController.__new__(ArgusController)
        ctrl._running = True
        ctrl.dome_driver = None
        ctrl.serial = MagicMock()
        ctrl.serial.connected = True
        from simulation_sensor import SimulationSensor
        ctrl.sensor = SimulationSensor()
        ctrl._emergency_stop()
        ctrl.serial.stop_motor.assert_called_once()

    def test_emergency_stop_calls_dome_abort(self):
        from main import ArgusController
        ctrl = ArgusController.__new__(ArgusController)
        ctrl._running = True
        ctrl.dome_driver = MagicMock()
        ctrl.serial = None
        from simulation_sensor import SimulationSensor
        ctrl.sensor = SimulationSensor()
        ctrl._emergency_stop()
        ctrl.dome_driver.abort.assert_called_once()

    def test_emergency_stop_tolerates_serial_error(self):
        from main import ArgusController
        ctrl = ArgusController.__new__(ArgusController)
        ctrl._running = True
        ctrl.dome_driver = None
        ctrl.serial = MagicMock()
        ctrl.serial.connected = True
        ctrl.serial.stop_motor.side_effect = RuntimeError("dead")
        from simulation_sensor import SimulationSensor
        ctrl.sensor = SimulationSensor()
        # Should not raise
        ctrl._emergency_stop()
        assert ctrl._running is False

    def test_crash_handler_calls_emergency_stop(self):
        from main import ArgusController
        ctrl = ArgusController.__new__(ArgusController)
        ctrl._running = True
        ctrl.dome_driver = None
        ctrl.serial = None
        from simulation_sensor import SimulationSensor
        ctrl.sensor = SimulationSensor()
        ctrl.sensor.slew_rate = 10.0
        ctrl._orig_excepthook = MagicMock()
        try:
            raise ValueError("test crash")
        except ValueError:
            exc_info = sys.exc_info()
        ctrl._crash_handler(*exc_info)
        assert ctrl.sensor.slew_rate == 0.0
        assert ctrl._running is False


# ---------------------------------------------------------------------------
# resolve_path
# ---------------------------------------------------------------------------
class TestResolvePath:
    """Verify that resolve_path checks both base path and _MEIPASS."""

    def test_resolve_existing_file(self):
        """resolve_path returns an existing file from the base path."""
        from path_utils import resolve_path
        result = resolve_path("config.yaml")
        assert result.name == "config.yaml"
        assert result.is_file()

    def test_resolve_existing_directory(self):
        """resolve_path returns an existing directory from the base path."""
        from path_utils import resolve_path
        result = resolve_path("assets")
        assert result.name == "assets"
        assert result.is_dir()

    def test_resolve_missing_returns_base_path(self):
        """resolve_path returns base_path / relative for missing resources."""
        from path_utils import resolve_path, get_base_path
        result = resolve_path("nonexistent_resource_xyz")
        assert result == get_base_path() / "nonexistent_resource_xyz"

    def test_resolve_checks_meipass_when_frozen(self, tmp_path):
        """In frozen mode, resolve_path falls back to sys._MEIPASS."""
        from path_utils import resolve_path
        # Create a fake file in a temp dir simulating _MEIPASS
        (tmp_path / "bundled_file.txt").write_text("data")
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
            result = resolve_path("bundled_file.txt")
            assert result.is_file()
            assert result.parent == tmp_path


# ---------------------------------------------------------------------------
# Settings dialog (Tab API compatibility)
# ---------------------------------------------------------------------------
class TestSettingsDialog:
    """Verify that the settings dialog uses the Flet 0.80+ Tabs API."""

    def test_show_settings_dialog_does_not_raise(self):
        """Calling show_settings_dialog must not crash (Tab API)."""
        from settings_gui import show_settings_dialog
        page = _make_mock_page()
        page.overlay = []
        show_settings_dialog(page, {}, lambda cfg: None)
        # Dialog was appended to overlay
        assert len(page.overlay) == 1


# ---------------------------------------------------------------------------
# Slit status
# ---------------------------------------------------------------------------
class TestSlitStatus:
    """Verify slit open/closed indicator and API."""

    def test_slit_indicator_exists(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.slit_indicator is not None
        assert gui.hint_slit is not None

    def test_slit_starts_closed(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui._slit_open is False
        assert gui.slit_indicator.bgcolor == COLOR_OFF

    def test_set_slit_status_open(self):
        gui = ArgusGUI(_make_mock_page())
        gui.set_slit_status(True)
        assert gui._slit_open is True
        assert gui.slit_indicator.bgcolor == COLOR_ON

    def test_set_slit_status_closed(self):
        gui = ArgusGUI(_make_mock_page())
        gui.set_slit_status(True)
        gui.set_slit_status(False)
        assert gui._slit_open is False
        assert gui.slit_indicator.bgcolor == COLOR_OFF


# ---------------------------------------------------------------------------
# Extended telemetry
# ---------------------------------------------------------------------------
class TestExtendedTelemetry:
    """Verify that extended telemetry fields are updated."""

    def test_extended_labels_exist(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.lbl_mount_alt is not None
        assert gui.lbl_sidereal is not None
        assert gui.lbl_tracking_rate is not None
        assert gui.lbl_pier_side is not None

    def test_update_telemetry_with_extras(self):
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(
            100.0, 98.0,
            mount_alt=45.5,
            sidereal_time="12:34:56",
            tracking_rate="Sidereal",
            pier_side="East",
        )
        assert "45.5" in gui.lbl_mount_alt.value
        assert "12:34:56" in gui.lbl_sidereal.value
        assert "Sidereal" in gui.lbl_tracking_rate.value
        assert "East" in gui.lbl_pier_side.value

    def test_update_telemetry_without_extras(self):
        """Extended fields should keep defaults when not provided."""
        gui = ArgusGUI(_make_mock_page())
        gui.update_telemetry(100.0, 98.0)
        assert "---" in gui.lbl_mount_alt.value
        assert "--:" in gui.lbl_sidereal.value


# ---------------------------------------------------------------------------
# Simulation controls
# ---------------------------------------------------------------------------
class TestSimulationControls:
    """Verify simulation slider and slit button widgets exist."""

    def test_sim_sliders_exist(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.sim_az_slider is not None
        assert gui.sim_alt_slider is not None

    def test_sim_az_slider_range(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.sim_az_slider.min == 0
        assert gui.sim_az_slider.max == 360

    def test_sim_alt_slider_range(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.sim_alt_slider.min == 0
        assert gui.sim_alt_slider.max == 90

    def test_sim_slit_button_exists(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.btn_sim_slit is not None

    def test_sim_card_in_dashboard(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui.sim_card is not None


# ---------------------------------------------------------------------------
# Theme cycling
# ---------------------------------------------------------------------------
class TestThemeCycling:
    """Verify the 3-step theme cycle: dark → day → night."""

    def test_initial_theme_is_dark(self):
        gui = ArgusGUI(_make_mock_page())
        assert gui._theme_cycle_index == 0
        assert gui._theme["bg"] == THEME_DARK["bg"]

    def test_cycle_to_day(self):
        from gui import THEME_DAY
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()
        assert gui._theme_cycle_index == 1
        assert gui._theme["bg"] == THEME_DAY["bg"]

    def test_cycle_to_night(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        gui.toggle_night_mode()  # → night
        assert gui._theme_cycle_index == 2
        assert gui._night_mode is True

    def test_cycle_back_to_dark(self):
        gui = ArgusGUI(_make_mock_page())
        gui.toggle_night_mode()  # → day
        gui.toggle_night_mode()  # → night
        gui.toggle_night_mode()  # → dark
        assert gui._theme_cycle_index == 0
        assert gui._night_mode is False
        assert gui._theme["bg"] == THEME_DARK["bg"]


# ---------------------------------------------------------------------------
# auto_mount parameter
# ---------------------------------------------------------------------------
class TestAutoMount:
    """Verify the auto_mount parameter controls page.add() calls."""

    def test_auto_mount_true_calls_add(self):
        page = _make_mock_page()
        ArgusGUI(page, auto_mount=True)
        page.add.assert_called_once()

    def test_auto_mount_false_skips_add(self):
        page = _make_mock_page()
        gui = ArgusGUI(page, auto_mount=False)
        page.add.assert_not_called()
        # But mount() should still work
        gui.mount()
        page.add.assert_called_once()
