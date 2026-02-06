"""
ARGUS - Advanced Rotation Guidance Using Sensors
Voice Feedback Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Provides threaded text-to-speech announcements so the GUI
stays responsive while the assistant speaks.
"""

import logging
import threading

logger = logging.getLogger(__name__)

try:
    import pyttsx3
except ImportError:                         # pragma: no cover
    pyttsx3 = None                          # type: ignore[assignment]


class VoiceAssistant:
    """Text-to-speech assistant that speaks in a background thread."""

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        if pyttsx3 is not None:
            try:
                self._engine = pyttsx3.init()
            except Exception as exc:        # pragma: no cover
                logger.warning("Could not initialise TTS engine: %s", exc)

    def say(self, text: str) -> None:
        """Speak *text* in a background thread.

        Args:
            text: The message to speak.
        """
        if self._engine is None:
            logger.info("VoiceAssistant (no engine): %s", text)
            return
        thread = threading.Thread(target=self._speak, args=(text,), daemon=True)
        thread.start()

    def _speak(self, text: str) -> None:
        """Internal: run the TTS engine (called from a worker thread)."""
        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as exc:        # pragma: no cover
                logger.error("TTS error: %s", exc)
