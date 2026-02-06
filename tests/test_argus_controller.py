"""Tests for the ArgusController class."""

import os
import sys
import time
from pathlib import Path

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Skip the whole module when no display is available (CI environments)
pytestmark = pytest.mark.skipif(
    not os.environ.get("DISPLAY"), reason="No display available"
)


@pytest.fixture(scope="module")
def controller():
    """Create a single ArgusController for all tests in this module."""
    from main import ArgusController
    ctrl = ArgusController()
    yield ctrl
    ctrl._running = False
    ctrl.app.destroy()


class TestArgusController:
    """Unit tests for ArgusController (requires a display)."""

    def test_button_bindings_set_slew_rate(self, controller):
        """Clicking CCW/STOP/CW should change the sensor slew rate."""
        controller.on_move_left()
        assert controller.sensor.slew_rate == -3.0

        controller.on_stop()
        assert controller.sensor.slew_rate == 0.0

        controller.on_move_right()
        assert controller.sensor.slew_rate == 3.0

    def test_control_loop_updates_sensor(self, controller):
        """The background thread should advance the sensor azimuth."""
        controller.sensor.slew_rate = 100.0  # fast for test
        start_az = controller.sensor.get_azimuth()
        # Give the daemon thread enough time to iterate
        for _ in range(40):
            time.sleep(0.05)
            if controller.sensor.get_azimuth() != start_az:
                break
        az = controller.sensor.get_azimuth()
        assert az != start_az, "Sensor azimuth should have changed"
        controller.sensor.slew_rate = 0.0
