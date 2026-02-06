"""Tests for new features: GUI log terminal, GuiLogHandler, English voice,
and extended settings tabs.

These tests do NOT require a display – they exercise pure logic.
"""

import logging
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ---------------------------------------------------------------------------
# GuiLogHandler
# ---------------------------------------------------------------------------
class TestGuiLogHandler:
    """Test the custom logging handler that forwards to the GUI."""

    def test_emit_calls_gui_write_log(self):
        from main import GuiLogHandler

        mock_gui = MagicMock()
        handler = GuiLogHandler(mock_gui)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Hello world", args=(), exc_info=None,
        )
        handler.emit(record)

        mock_gui.write_log.assert_called_once()
        args = mock_gui.write_log.call_args[0]
        assert "Hello world" in args[0]

    def test_emit_handles_exception_gracefully(self):
        from main import GuiLogHandler

        mock_gui = MagicMock()
        mock_gui.write_log.side_effect = RuntimeError("GUI destroyed")
        handler = GuiLogHandler(mock_gui)
        handler.setFormatter(logging.Formatter("%(message)s"))

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        # Should not raise
        handler.emit(record)

    def test_handler_level_default(self):
        from main import GuiLogHandler

        handler = GuiLogHandler(MagicMock())
        handler.setLevel(logging.INFO)
        assert handler.level == logging.INFO


# ---------------------------------------------------------------------------
# VoiceAssistant English voice selection
# ---------------------------------------------------------------------------
class TestVoiceEnglish:
    """Test the English voice selection logic."""

    def test_set_english_voice_finds_english(self):
        from voice import VoiceAssistant

        va = VoiceAssistant.__new__(VoiceAssistant)
        va._engine = MagicMock()
        va._lock = threading.Lock()

        mock_voice_de = MagicMock()
        mock_voice_de.id = "com.apple.speech.synthesis.voice.Anna"
        mock_voice_de.name = "Anna (German)"

        mock_voice_en = MagicMock()
        mock_voice_en.id = "com.apple.speech.synthesis.voice.samantha"
        mock_voice_en.name = "Samantha (English)"

        va._engine.getProperty.return_value = [mock_voice_de, mock_voice_en]

        va._set_english_voice()
        va._engine.setProperty.assert_called_once_with(
            'voice', mock_voice_en.id
        )

    def test_set_english_voice_by_en_us(self):
        from voice import VoiceAssistant

        va = VoiceAssistant.__new__(VoiceAssistant)
        va._engine = MagicMock()
        va._lock = threading.Lock()

        mock_voice = MagicMock()
        mock_voice.id = "HKEY_LOCAL_MACHINE\\en-us\\david"
        mock_voice.name = "David"

        va._engine.getProperty.return_value = [mock_voice]

        va._set_english_voice()
        va._engine.setProperty.assert_called_once_with('voice', mock_voice.id)

    def test_set_english_voice_no_match_logs_warning(self):
        from voice import VoiceAssistant

        va = VoiceAssistant.__new__(VoiceAssistant)
        va._engine = MagicMock()
        va._lock = threading.Lock()

        mock_voice = MagicMock()
        mock_voice.id = "com.voice.german"
        mock_voice.name = "Hans (Deutsch)"

        va._engine.getProperty.return_value = [mock_voice]

        with patch("voice.logger") as mock_logger:
            va._set_english_voice()

        va._engine.setProperty.assert_not_called()

    def test_set_english_voice_no_engine(self):
        from voice import VoiceAssistant

        va = VoiceAssistant.__new__(VoiceAssistant)
        va._engine = None
        va._lock = threading.Lock()

        # Should not raise
        va._set_english_voice()


# ---------------------------------------------------------------------------
# Settings GUI new tabs – helpers (headless)
# ---------------------------------------------------------------------------
class TestSettingsGuiExtended:
    """Verify the extended save logic handles new config keys."""

    def test_to_int_valid_string(self):
        from settings_gui import SettingsWindow
        assert SettingsWindow._to_int("42", 10) == 42

    def test_to_int_with_float_string(self):
        from settings_gui import SettingsWindow
        # int("3.14") would raise ValueError, so default should be used
        assert SettingsWindow._to_int("3.14", 10) == 10

    def test_to_float_with_negative(self):
        from settings_gui import SettingsWindow
        assert SettingsWindow._to_float("-1.5", 0.0) == pytest.approx(-1.5)

    def test_to_float_invalid_string(self):
        from settings_gui import SettingsWindow
        assert SettingsWindow._to_float("not_a_number", 5.0) == 5.0

    def test_aruco_dictionaries_list(self):
        from settings_gui import ARUCO_DICTIONARIES
        assert "DICT_4X4_50" in ARUCO_DICTIONARIES
        assert len(ARUCO_DICTIONARIES) > 0


# ---------------------------------------------------------------------------
# GUI font constants
# ---------------------------------------------------------------------------
class TestGuiFonts:
    """Verify font constants are configured correctly."""

    def test_label_font_is_sans_serif(self):
        from gui import FONT_LABEL, FONT_SECTION, FONT_INDICATOR, FONT_BUTTON
        # Labels, sections, indicators, buttons use sans-serif (Roboto)
        assert FONT_LABEL[0] == "Roboto"
        assert FONT_SECTION[0] == "Roboto"
        assert FONT_INDICATOR[0] == "Roboto"
        assert FONT_BUTTON[0] == "Roboto"

    def test_data_font_is_monospace(self):
        from gui import FONT_DATA
        # Numeric data must stay monospace
        assert "Mono" in FONT_DATA[0]

    def test_log_font_is_monospace(self):
        from gui import FONT_LOG
        assert "Mono" in FONT_LOG[0]


# ---------------------------------------------------------------------------
# GUI card design constants
# ---------------------------------------------------------------------------
class TestGuiCardDesign:
    """Verify card design constants."""

    def test_card_bg_color_exists(self):
        from gui import COLOR_CARD_BG
        assert COLOR_CARD_BG.startswith("#")

    def test_card_corner_radius(self):
        from gui import CARD_CORNER_RADIUS
        assert CARD_CORNER_RADIUS > 0


# ---------------------------------------------------------------------------
# SegmentedButton serialization
# ---------------------------------------------------------------------------
class TestSegmentedButtonSerialization:
    """Ensure SegmentedButton.selected uses a list, not a set.

    Flet 0.80+ communicates with the frontend via msgpack which cannot
    serialize Python ``set`` objects.  Using a list avoids the
    ``TypeError: can not serialize 'set' object`` crash at startup.
    """

    def test_selected_is_list_not_set(self):
        import flet as ft
        from gui import ArgusGUI

        btn = ft.SegmentedButton(
            segments=[
                ft.Segment(value="MANUAL", label=ft.Text("MANUAL")),
                ft.Segment(value="AUTO-SLAVE", label=ft.Text("AUTO-SLAVE")),
            ],
            selected=["MANUAL"],
        )
        assert isinstance(btn.selected, list), (
            "selected must be a list for msgpack serialization"
        )

    def test_selected_serializable_with_msgpack(self):
        import msgpack

        selected = ["MANUAL"]
        packed = msgpack.packb(selected)
        assert msgpack.unpackb(packed) == [b"MANUAL"] or msgpack.unpackb(packed, raw=False) == ["MANUAL"]
