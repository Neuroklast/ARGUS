"""
ARGUS - Advanced Rotation Guidance Using Sensors
Calibration Module

Provides an OffsetSolver that computes mount GEM offsets (east, north)
and pier height from a set of measured calibration points using
scipy.optimize.least_squares.
"""

import logging
from typing import Dict, List, Optional

import numpy as np
from scipy.optimize import least_squares

logger = logging.getLogger(__name__)


class OffsetSolver:
    """Solve for GEM mount offsets using measured dome-azimuth residuals.

    Collect calibration points where the dome slit is visually centred,
    then call :meth:`solve` to find the best-fit offsets.
    """

    def __init__(self) -> None:
        self._points: List[Dict[str, float]] = []

    def add_point(
        self, telescope_az: float, telescope_alt: float, dome_az: float
    ) -> None:
        """Record a single calibration measurement.

        Args:
            telescope_az:  Telescope azimuth in degrees.
            telescope_alt: Telescope altitude in degrees.
            dome_az:       Observed dome azimuth (slit centred) in degrees.
        """
        self._points.append(
            {
                "telescope_az": telescope_az,
                "telescope_alt": telescope_alt,
                "dome_az": dome_az,
            }
        )
        logger.debug(
            "Calibration point added: tel_az=%.1f, tel_alt=%.1f, dome_az=%.1f",
            telescope_az,
            telescope_alt,
            dome_az,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _predicted_dome_az(
        telescope_az: float,
        telescope_alt: float,
        offset_east: float,
        offset_north: float,
        pier_height: float,
    ) -> float:
        """Compute the expected dome azimuth given offsets.

        Uses a simplified geometric model: the telescope optical axis
        originates from (offset_east, offset_north, pier_height) and
        the dome slit azimuth is the horizontal angle of that vector.
        """
        az_rad = np.radians(telescope_az)
        alt_rad = np.radians(telescope_alt)

        x = offset_east + np.cos(alt_rad) * np.sin(az_rad)
        y = offset_north + np.cos(alt_rad) * np.cos(az_rad)

        predicted_az = np.degrees(np.arctan2(x, y)) % 360.0
        return predicted_az

    def _residuals(self, params: np.ndarray) -> np.ndarray:
        """Return the vector of azimuth residuals for *least_squares*."""
        offset_east, offset_north, pier_height = params
        res = []
        for pt in self._points:
            predicted = self._predicted_dome_az(
                pt["telescope_az"],
                pt["telescope_alt"],
                offset_east,
                offset_north,
                pier_height,
            )
            diff = predicted - pt["dome_az"]
            # Wrap to ±180°
            if diff > 180:
                diff -= 360
            elif diff < -180:
                diff += 360
            res.append(diff)
        return np.array(res)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def solve(self) -> Optional[Dict[str, float]]:
        """Run the least-squares optimiser and return the best-fit offsets.

        Returns:
            Dictionary with ``gem_offset_east``, ``gem_offset_north`` and
            ``pier_height``, or ``None`` if there are fewer than 3 points.
        """
        if len(self._points) < 3:
            logger.error(
                "Need at least 3 calibration points, got %d", len(self._points)
            )
            return None

        x0 = np.array([0.0, 0.0, 1.5])
        result = least_squares(self._residuals, x0)

        offsets = {
            "gem_offset_east": float(result.x[0]),
            "gem_offset_north": float(result.x[1]),
            "pier_height": float(result.x[2]),
        }
        logger.info("Calibration solved: %s (cost=%.4f)", offsets, result.cost)
        return offsets
