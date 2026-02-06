"""Tests for the dome driver abstraction layer.

These tests do NOT require real hardware – all serial communication
is mocked.
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dome_drivers import (
    ArgusProtocol,
    DomeDriver,
    EncoderDriver,
    LesveDomeProtocol,
    RelayProtocol,
    StepperDriver,
    TimedDriver,
    create_driver,
    get_protocol,
)


# ---------------------------------------------------------------------------
# Protocol translators
# ---------------------------------------------------------------------------
class TestArgusProtocol:
    def test_move_to(self):
        p = ArgusProtocol()
        assert p.move_to(90.5, 60) == "MOVE 90.50 60"

    def test_stop(self):
        assert ArgusProtocol().stop() == "STOP"

    def test_poll(self):
        assert ArgusProtocol().poll_position() == "STATUS"

    def test_home(self):
        assert ArgusProtocol().home("cw") == "HOME CW"


class TestLesveDomeProtocol:
    def test_move_to(self):
        p = LesveDomeProtocol()
        assert p.move_to(180.0) == "G 180.0"

    def test_stop(self):
        assert LesveDomeProtocol().stop() == "S"

    def test_poll(self):
        assert LesveDomeProtocol().poll_position() == "P"

    def test_home(self):
        assert LesveDomeProtocol().home("CCW") == "H"


class TestRelayProtocol:
    def test_move_to(self):
        assert RelayProtocol().move_to(90) == "RELAY CW"

    def test_stop(self):
        assert RelayProtocol().stop() == "RELAY OFF"


class TestGetProtocol:
    def test_argus(self):
        assert isinstance(get_protocol("argus"), ArgusProtocol)

    def test_lesvedome(self):
        assert isinstance(get_protocol("lesvedome"), LesveDomeProtocol)

    def test_relay(self):
        assert isinstance(get_protocol("relay"), RelayProtocol)

    def test_default(self):
        assert isinstance(get_protocol(""), ArgusProtocol)

    def test_none(self):
        assert isinstance(get_protocol(None), ArgusProtocol)


# ---------------------------------------------------------------------------
# StepperDriver
# ---------------------------------------------------------------------------
class TestStepperDriver:
    def _make(self, serial=None):
        cfg = {"hardware": {
            "motor_type": "stepper",
            "protocol": "argus",
            "steps_per_degree": 200.0,
        }}
        return StepperDriver(cfg, serial)

    def test_initial_position(self):
        d = self._make()
        assert d.position == 0.0

    def test_slew_sets_position(self):
        d = self._make()
        d.slew_to(90.0)
        assert d.position == pytest.approx(90.0)

    def test_slew_normalizes(self):
        d = self._make()
        d.slew_to(400.0)
        assert d.position == pytest.approx(40.0)

    def test_slew_sends_command(self):
        ser = MagicMock()
        ser.send_command.return_value = True
        d = self._make(ser)
        d.slew_to(90.0)
        ser.send_command.assert_called()

    def test_not_slewing_after_move(self):
        d = self._make()
        d.slew_to(45.0)
        assert d.slewing is False

    def test_abort(self):
        d = self._make()
        d.abort()
        assert d.slewing is False

    def test_update_is_noop(self):
        d = self._make()
        d.slew_to(90.0)
        d.update(0.1)
        assert d.position == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# EncoderDriver
# ---------------------------------------------------------------------------
class TestEncoderDriver:
    def _make(self, serial=None):
        cfg = {"hardware": {
            "motor_type": "encoder",
            "protocol": "argus",
            "ticks_per_degree": 50.0,
            "encoder_tolerance": 1.0,
        }}
        return EncoderDriver(cfg, serial)

    def test_slew_starts_slewing(self):
        d = self._make()
        d.slew_to(180.0)
        assert d.slewing is True

    def test_update_stops_when_within_tolerance(self):
        d = self._make()
        d.slew_to(180.0)
        d.feed_encoder(179.5)
        d.update(0.1)
        assert d.slewing is False

    def test_update_continues_when_outside_tolerance(self):
        d = self._make()
        d.slew_to(180.0)
        d.feed_encoder(170.0)
        d.update(0.1)
        assert d.slewing is True

    def test_feed_encoder_updates_position(self):
        d = self._make()
        d.feed_encoder(123.4)
        assert d.position == pytest.approx(123.4)

    def test_abort(self):
        d = self._make()
        d.slew_to(90.0)
        d.abort()
        assert d.slewing is False


# ---------------------------------------------------------------------------
# TimedDriver
# ---------------------------------------------------------------------------
class TestTimedDriver:
    def _make(self, serial=None):
        cfg = {"hardware": {
            "motor_type": "timed",
            "protocol": "argus",
            "degrees_per_second": 10.0,
        }}
        return TimedDriver(cfg, serial)

    def test_slew_starts_slewing(self):
        d = self._make()
        d.slew_to(50.0)
        assert d.slewing is True

    def test_update_advances_position(self):
        d = self._make()
        d.slew_to(50.0)
        d.update(1.0)  # 10°/s × 1s = 10°
        assert d.position > 0.0

    def test_reaches_target(self):
        d = self._make()
        d.slew_to(20.0)
        # Run enough updates to cover 20° at 10°/s
        for _ in range(30):
            d.update(0.1)
        assert d.slewing is False
        assert d.position == pytest.approx(20.0)

    def test_abort_stops(self):
        d = self._make()
        d.slew_to(100.0)
        d.abort()
        assert d.slewing is False

    def test_shortest_path_ccw(self):
        d = self._make()
        d.position = 10.0
        d.slew_to(350.0)
        # Should go CCW (shorter path)
        assert d._direction == -1.0


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
class TestCreateDriver:
    def test_stepper(self):
        cfg = {"hardware": {"motor_type": "stepper"}}
        assert isinstance(create_driver(cfg), StepperDriver)

    def test_encoder(self):
        cfg = {"hardware": {"motor_type": "encoder"}}
        assert isinstance(create_driver(cfg), EncoderDriver)

    def test_timed(self):
        cfg = {"hardware": {"motor_type": "timed"}}
        assert isinstance(create_driver(cfg), TimedDriver)

    def test_default_is_stepper(self):
        assert isinstance(create_driver({}), StepperDriver)


# ---------------------------------------------------------------------------
# Homing
# ---------------------------------------------------------------------------
class TestHoming:
    def test_home_sets_position(self):
        cfg = {"hardware": {"motor_type": "stepper"}}
        d = StepperDriver(cfg)
        d.home(home_az=180.0, direction="CW")
        assert d.position == pytest.approx(180.0)

    def test_home_stops_slewing(self):
        cfg = {"hardware": {"motor_type": "stepper"}}
        d = StepperDriver(cfg)
        d.home(home_az=90.0)
        assert d.slewing is False
