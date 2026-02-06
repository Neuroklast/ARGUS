"""Tests for the SimulationSensor class."""

import sys
from pathlib import Path

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simulation_sensor import SimulationSensor


class TestSimulationSensor:
    """Unit tests for SimulationSensor."""

    def test_initial_state(self):
        sensor = SimulationSensor()
        assert sensor.get_azimuth() == 0.0
        assert sensor.slew_rate == 0.0

    def test_no_movement_when_slew_rate_zero(self):
        sensor = SimulationSensor()
        sensor.update(1.0)
        assert sensor.get_azimuth() == 0.0

    def test_positive_slew_rate(self):
        sensor = SimulationSensor()
        sensor.slew_rate = 10.0
        sensor.update(1.0)
        assert sensor.get_azimuth() == 10.0

    def test_negative_slew_rate(self):
        sensor = SimulationSensor()
        sensor.slew_rate = -3.0
        sensor.update(1.0)
        # -3.0 % 360.0 == 357.0
        assert sensor.get_azimuth() == 357.0

    def test_wraps_past_360(self):
        sensor = SimulationSensor()
        sensor.slew_rate = 100.0
        sensor.update(4.0)  # 400 degrees -> 40 degrees
        assert abs(sensor.get_azimuth() - 40.0) < 1e-9

    def test_accumulates_over_multiple_updates(self):
        sensor = SimulationSensor()
        sensor.slew_rate = 5.0
        sensor.update(1.0)
        sensor.update(1.0)
        assert abs(sensor.get_azimuth() - 10.0) < 1e-9

    def test_slew_rate_can_be_changed(self):
        sensor = SimulationSensor()
        sensor.slew_rate = 3.0
        sensor.update(1.0)
        sensor.slew_rate = 0.0
        sensor.update(1.0)
        assert abs(sensor.get_azimuth() - 3.0) < 1e-9
