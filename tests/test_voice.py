"""Tests for the VoiceAssistant class.

These tests do NOT require audio hardware – they exercise the
interface and threading behaviour of ``src/voice.py``.
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from voice import VoiceAssistant


class TestVoiceAssistant:
    """Unit tests for VoiceAssistant."""

    def test_say_without_engine_does_not_raise(self):
        """When pyttsx3 is unavailable the assistant should log, not crash."""
        va = VoiceAssistant.__new__(VoiceAssistant)
        va._engine = None
        va._lock = __import__("threading").Lock()
        # Should simply return without error
        va.say("Hello")

    def test_say_spawns_thread(self):
        """say() should start a daemon thread for each call."""
        va = VoiceAssistant.__new__(VoiceAssistant)
        va._engine = MagicMock()
        va._lock = __import__("threading").Lock()
        va.say("Testing thread")
        # Give thread a moment to start
        time.sleep(0.2)
        va._engine.say.assert_called_once_with("Testing thread")
        va._engine.runAndWait.assert_called_once()

    @patch("voice.pyttsx3", None)
    def test_init_without_pyttsx3(self):
        """VoiceAssistant should init gracefully when pyttsx3 is missing."""
        va = VoiceAssistant()
        assert va._engine is None
        # say() should not raise
        va.say("no engine")
