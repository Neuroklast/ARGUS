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
                self._set_english_voice()
            except Exception as exc:        # pragma: no cover
                logger.warning("Could not initialise TTS engine: %s", exc)

    def _set_english_voice(self):
        """Attempt to select an English voice for the TTS engine."""
        if self._engine is None:
            return
        try:
            voices = self._engine.getProperty('voices')
            if not voices:
                return
            for voice in voices:
                voice_id = (voice.id or "").lower()
                voice_name = (voice.name or "").lower()
                combined = voice_id + " " + voice_name
                if any(tag in combined for tag in ("english", "en-us", "en-gb", "en_us", "en_gb")):
                    self._engine.setProperty('voice', voice.id)
                    logger.info("English voice selected: %s", voice.name)
                    return
            logger.warning("No English voice found – using system default")
        except Exception as exc:
            logger.warning("Could not set English voice: %s", exc)

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
