"""Tests for the red_night theme and new GUI features.

These tests validate the theme JSON structure and new GUI widgets
without requiring a full display (theme file tests are headless).
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

THEME_PATH = Path(__file__).resolve().parent.parent / "assets" / "themes" / "red_night.json"


class TestRedNightTheme:
    """Validate the red_night.json theme file."""

    def test_theme_file_exists(self):
        assert THEME_PATH.is_file(), "red_night.json should exist"

    def test_theme_is_valid_json(self):
        data = json.loads(THEME_PATH.read_text())
        assert isinstance(data, dict)

    def test_theme_contains_required_widgets(self):
        data = json.loads(THEME_PATH.read_text())
        for widget in ("CTk", "CTkButton", "CTkFrame", "CTkLabel", "CTkSwitch"):
            assert widget in data, f"Theme should define {widget}"

    def test_no_blue_colours(self):
        """The theme must not contain any blue-ish hex colours."""
        text = THEME_PATH.read_text()
        # Common blue hex values that should NOT appear
        blue_patterns = ["#1F6AA5", "#144870", "#3B8ED0", "#36719F"]
        for pattern in blue_patterns:
            assert pattern not in text, f"Blue colour {pattern} found in theme"


# GUI tests require a display
pytestmark_gui = pytest.mark.skipif(
    not os.environ.get("DISPLAY"), reason="No display available"
)


@pytestmark_gui
class TestGuiRadarAndSettings:
    """Tests for the new radar widget and settings section."""

    @pytest.fixture(autouse=True)
    def setup_app(self):
        import customtkinter as ctk
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")
        from gui import ArgusApp
        self.app = ArgusApp()
        yield
        self.app.destroy()

    def test_radar_canvas_exists(self):
        assert hasattr(self.app, "radar_canvas")

    def test_draw_radar_runs(self):
        """draw_radar should execute without errors."""
        self.app.draw_radar(45.0, 90.0)

    def test_night_mode_switch_exists(self):
        assert hasattr(self.app, "night_mode_switch")
        assert hasattr(self.app, "night_mode_var")

    def test_update_telemetry_includes_radar(self):
        """update_telemetry should update text and radar."""
        self.app.update_telemetry(123.4, 56.7)
        assert "123.4" in self.app.lbl_mount_az.cget("text")
        assert "056.7" in self.app.lbl_dome_az.cget("text")
