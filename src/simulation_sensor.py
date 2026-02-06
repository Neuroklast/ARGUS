"""
ARGUS - Advanced Rotation Guidance Using Sensors
Simulation Sensor Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Provides a simple simulated dome sensor for testing the GUI
without requiring real hardware.
"""


class SimulationSensor:
    """Simulated dome azimuth sensor driven by a configurable slew rate."""

    def __init__(self):
        self._azimuth = 0.0
        self.slew_rate = 0.0  # degrees per second

    def update(self, dt: float) -> None:
        """Advance the simulated azimuth by *slew_rate * dt*.

        Args:
            dt: Elapsed time in seconds since the last update.
        """
        self._azimuth = (self._azimuth + self.slew_rate * dt) % 360.0

    def get_azimuth(self) -> float:
        """Return the current simulated dome azimuth in degrees."""
        return self._azimuth
