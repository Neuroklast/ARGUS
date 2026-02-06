"""
ARGUS - Advanced Rotation Guidance Using Sensors
Replay ASCOM Handler Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Provides a mock ASCOM handler that replays recorded telescope data
from a list of calibration records (loaded via :mod:`data_loader`).
"""

import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ReplayASCOMHandler:
    """Mock ASCOM handler that replays pre-recorded calibration data.

    This class exposes the same public API as
    :class:`ascom_handler.ASCOMHandler` so that it can be used as a
    drop-in replacement during demo/replay mode.

    Parameters
    ----------
    data : list[dict]
        List of record dictionaries as returned by
        :func:`data_loader.load_calibration_data`.
    speed : float, optional
        Playback speed multiplier (default ``1.0``).  Use values > 1
        for accelerated replay.
    """

    def __init__(self, data: List[Dict], speed: float = 1.0):
        if not data:
            raise ValueError("Replay data must not be empty")

        self.data = data
        self.speed = max(speed, 0.01)
        self.connected = True

        # Time references
        self._start_wall = time.time()
        self._start_data = data[0]["timestamp"].timestamp()
        self._data_duration = (
            data[-1]["timestamp"].timestamp() - self._start_data
        )

        self._index = 0
        logger.info(
            "ReplayASCOMHandler ready – %d records, %.0fs duration, speed=%.1fx",
            len(data), self._data_duration, self.speed,
        )

    # -- internal helpers ------------------------------------------------

    def _current_data_time(self) -> float:
        """Return the current position in data-time (epoch seconds)."""
        elapsed_wall = time.time() - self._start_wall
        return self._start_data + elapsed_wall * self.speed

    def _nearest_record(self) -> Dict:
        """Return the record closest to the current playhead time."""
        target = self._current_data_time()
        best = self.data[self._index]
        best_diff = abs(best["timestamp"].timestamp() - target)

        for i in range(max(0, self._index - 1), len(self.data)):
            diff = abs(self.data[i]["timestamp"].timestamp() - target)
            if diff < best_diff:
                best_diff = diff
                best = self.data[i]
                self._index = i
            elif diff > best_diff:
                # Past the closest point – stop searching
                break

        return best

    def record_at_index(self, index: int) -> Dict:
        """Return the record at an explicit index (for testing)."""
        return self.data[max(0, min(index, len(self.data) - 1))]

    # -- public API (mirrors ASCOMHandler) -------------------------------

    def connect(self) -> bool:
        """No-op – always returns True."""
        self.connected = True
        return True

    def disconnect(self) -> None:
        """No-op."""
        self.connected = False

    def get_position(self) -> Optional[Dict[str, float]]:
        """Return the replayed telescope position (nearest-neighbour)."""
        rec = self._nearest_record()
        return {
            "ra": rec["ra"],
            "dec": rec["dec"],
            "altitude": rec["alt"],
            "azimuth": rec["az"],
        }

    def get_side_of_pier(self) -> Optional[int]:
        """Return the replayed side-of-pier value."""
        return self._nearest_record()["pier_side"]

    def get_tracking_state(self) -> bool:
        """Return ``True`` when the status indicates active tracking."""
        status = self._nearest_record()["status"]
        return status in ("TRACKING", "TRACKING_RESUMED")

    def get_all_data(self) -> Optional[Dict]:
        """Return combined telescope data (mirrors ASCOMHandler)."""
        pos = self.get_position()
        if pos is None:
            return None
        return {
            **pos,
            "side_of_pier": self.get_side_of_pier(),
            "tracking": self.get_tracking_state(),
        }

    def get_site_data(self) -> Optional[Dict[str, float]]:
        """Return fixed site coordinates (from header metadata)."""
        return {
            "latitude": 51.17,
            "longitude": 7.08,
            "elevation": 0.0,
        }

    @property
    def current_status(self) -> str:
        """Return the current STATUS string from the replay data."""
        return self._nearest_record()["status"]
