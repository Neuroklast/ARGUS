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

    def test_update_telemetry_calls_page_update(self):
        page = _make_mock_page()
        gui = ArgusGUI(page)
        page.update.reset_mock()
        gui.update_telemetry(0.0, 0.0)
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
        """Expect circle + mount line + dome arc = 3 shapes."""
        shapes = ArgusGUI._radar_shapes(45.0, 90.0)
        assert len(shapes) == 3

    def test_draw_radar_updates_canvas(self):
        gui = ArgusGUI(_make_mock_page())
        gui.draw_radar(180.0, 270.0)
        assert len(gui.radar_canvas.shapes) == 3


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
