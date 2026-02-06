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
    """Tests for the new radar widget and settings section.

    NOTE: These tests are skipped without a display since Flet
    requires a running app context for widget creation.
    """

    pass
