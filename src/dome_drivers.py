"""
ARGUS - Advanced Rotation Guidance Using Sensors
Dome Driver Abstraction Layer

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Provides a hardware-agnostic driver interface for dome motor control.
Three concrete implementations cover the most common drive types:

* **StepperDriver** – open-loop stepper motors (position = steps)
* **EncoderDriver** – DC motors with encoder feedback (closed-loop)
* **TimedDriver**   – relay-driven motors without sensors (dead reckoning)

A protocol translation layer allows switching between the native ARGUS
serial protocol, the LesveDome industry-standard emulation, and a
simple relay control scheme.
"""

import abc
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol translators
# ---------------------------------------------------------------------------
class ProtocolTranslator(abc.ABC):
    """Translate high-level dome commands into wire-format strings."""

    @abc.abstractmethod
    def move_to(self, position: float, speed: int = 50) -> str:
        """Return the command string for a GoTo move."""

    @abc.abstractmethod
    def stop(self) -> str:
        """Return the command string for an emergency stop."""

    @abc.abstractmethod
    def poll_position(self) -> str:
        """Return the command string for a position query."""

    @abc.abstractmethod
    def home(self, direction: str) -> str:
        """Return the command string for a homing (reference) move."""


class ArgusProtocol(ProtocolTranslator):
    """Native ARGUS serial protocol (``MOVE az speed``, ``STOP``, …)."""

    def move_to(self, position: float, speed: int = 50) -> str:
        return f"MOVE {position:.2f} {speed}"

    def stop(self) -> str:
        return "STOP"

    def poll_position(self) -> str:
        return "STATUS"

    def home(self, direction: str) -> str:
        return f"HOME {direction.upper()}"


class LesveDomeProtocol(ProtocolTranslator):
    """LesveDome industry-standard command set."""

    def move_to(self, position: float, speed: int = 50) -> str:
        return f"G {position:.1f}"

    def stop(self) -> str:
        return "S"

    def poll_position(self) -> str:
        return "P"

    def home(self, direction: str) -> str:
        return "H"


class RelayProtocol(ProtocolTranslator):
    """Simple relay ON/OFF protocol for time-based motors."""

    def move_to(self, position: float, speed: int = 50) -> str:
        # Relay motors don't support absolute positioning; the caller
        # (TimedDriver) determines direction.  Default to CW.
        return "RELAY CW"

    def stop(self) -> str:
        return "RELAY OFF"

    def poll_position(self) -> str:
        return "STATUS"

    def home(self, direction: str) -> str:
        return f"RELAY {direction.upper()}"


def get_protocol(name: str) -> ProtocolTranslator:
    """Factory that returns a protocol translator by config name."""
    name = (name or "argus").lower().strip()
    if name == "lesvedome":
        return LesveDomeProtocol()
    if name == "relay":
        return RelayProtocol()
    return ArgusProtocol()


# ---------------------------------------------------------------------------
# Abstract dome driver
# ---------------------------------------------------------------------------
class DomeDriver(abc.ABC):
    """Base class for all dome motor drivers.

    Every driver tracks a *virtual position* (degrees 0-360) and
    exposes a uniform interface to the controller.
    """

    def __init__(self, config: dict, serial_ctrl=None):
        self._position: float = 0.0
        self._target: Optional[float] = None
        self._slewing: bool = False
        self._lock = threading.Lock()
        self._serial = serial_ctrl
        self._protocol = get_protocol(
            config.get("hardware", {}).get("protocol", "argus")
        )
        self._config = config

    # -- Public properties --------------------------------------------------
    @property
    def position(self) -> float:
        """Current dome azimuth in degrees [0, 360)."""
        with self._lock:
            return self._position % 360.0

    @position.setter
    def position(self, value: float) -> None:
        with self._lock:
            self._position = value % 360.0

    @property
    def slewing(self) -> bool:
        """``True`` while the dome is moving towards a target."""
        with self._lock:
            return self._slewing

    # -- Abstract interface -------------------------------------------------
    @abc.abstractmethod
    def slew_to(self, target_az: float, speed: int = 50) -> None:
        """Start moving toward *target_az* (non-blocking)."""

    @abc.abstractmethod
    def abort(self) -> None:
        """Immediately stop any movement."""

    @abc.abstractmethod
    def update(self, dt: float) -> None:
        """Called every control-loop tick with elapsed time *dt*."""

    # -- Homing (default implementation) ------------------------------------
    def home(self, home_az: float = 0.0, direction: str = "CW") -> None:
        """Start a homing (reference) run.

        The default implementation simply sends a HOME command and sets
        the internal position to *home_az* when it arrives.  Subclasses
        may override for sensor-based homing.
        """
        logger.info("Homing: seeking switch at %.1f° (%s)", home_az, direction)
        if self._serial:
            cmd = self._protocol.home(direction)
            self._serial.send_command(cmd)
        self.position = home_az
        with self._lock:
            self._slewing = False

    # -- Helper: send a command via the serial port -------------------------
    def _send(self, command: str) -> bool:
        if self._serial is None:
            return False
        return self._serial.send_command(command)


# ---------------------------------------------------------------------------
# Stepper motor driver (open-loop)
# ---------------------------------------------------------------------------
class StepperDriver(DomeDriver):
    """Driver for stepper motors with a known steps-per-degree ratio.

    The motor is assumed to hold position exactly (open-loop).  The
    controller calculates the absolute step count from the target
    azimuth and the calibration factor.
    """

    def __init__(self, config: dict, serial_ctrl=None):
        super().__init__(config, serial_ctrl)
        hw = config.get("hardware", {})
        self._steps_per_degree: float = hw.get("steps_per_degree", 100.0)

    def slew_to(self, target_az: float, speed: int = 50) -> None:
        target_az = target_az % 360.0
        with self._lock:
            self._target = target_az
            self._slewing = True

        steps = int(target_az * self._steps_per_degree)
        logger.debug("Stepper: slew to %.2f° (%d steps)", target_az, steps)

        cmd = self._protocol.move_to(target_az, speed)
        self._send(cmd)

        # Stepper is assumed to reach the target immediately
        with self._lock:
            self._position = target_az
            self._slewing = False
            self._target = None

    def abort(self) -> None:
        cmd = self._protocol.stop()
        self._send(cmd)
        with self._lock:
            self._slewing = False
            self._target = None

    def update(self, dt: float) -> None:
        # Stepper holds position – nothing to update
        pass


# ---------------------------------------------------------------------------
# Encoder-feedback driver (closed-loop)
# ---------------------------------------------------------------------------
class EncoderDriver(DomeDriver):
    """Driver for DC motors with encoder feedback (closed-loop).

    The motor runs until encoder ticks match the target position.
    A configurable tolerance band prevents oscillation at the setpoint.
    """

    def __init__(self, config: dict, serial_ctrl=None):
        super().__init__(config, serial_ctrl)
        hw = config.get("hardware", {})
        self._ticks_per_degree: float = hw.get("ticks_per_degree", 50.0)
        self._tolerance: float = hw.get("encoder_tolerance", 0.5)

    def slew_to(self, target_az: float, speed: int = 50) -> None:
        target_az = target_az % 360.0
        with self._lock:
            self._target = target_az
            self._slewing = True

        logger.debug("Encoder: slew to %.2f° (tol=%.1f°)", target_az, self._tolerance)
        cmd = self._protocol.move_to(target_az, speed)
        self._send(cmd)

    def abort(self) -> None:
        cmd = self._protocol.stop()
        self._send(cmd)
        with self._lock:
            self._slewing = False
            self._target = None

    def update(self, dt: float) -> None:
        """Check encoder feedback and stop when within tolerance."""
        with self._lock:
            if not self._slewing or self._target is None:
                return
            target = self._target
            pos = self._position

        error = abs(target - pos)
        if error > 180:
            error = 360 - error

        if error <= self._tolerance:
            logger.debug("Encoder: target reached (error=%.2f°)", error)
            self.abort()

    def feed_encoder(self, current_degrees: float) -> None:
        """Update the internal position from encoder feedback.

        Called by the serial controller when encoder data arrives.
        """
        with self._lock:
            self._position = current_degrees % 360.0


# ---------------------------------------------------------------------------
# Time-based (relay) driver – dead reckoning
# ---------------------------------------------------------------------------
class TimedDriver(DomeDriver):
    """Driver for relay-controlled motors without position feedback.

    Estimates position via dead reckoning using the configured
    *degrees_per_second* rate.
    """

    def __init__(self, config: dict, serial_ctrl=None):
        super().__init__(config, serial_ctrl)
        hw = config.get("hardware", {})
        self._deg_per_sec: float = hw.get("degrees_per_second", 5.0)
        self._direction: float = 0.0  # +1 CW, -1 CCW, 0 stopped

    def slew_to(self, target_az: float, speed: int = 50) -> None:
        target_az = target_az % 360.0
        with self._lock:
            self._target = target_az
            self._slewing = True

        # Choose shortest rotation direction
        diff = (target_az - self._position) % 360.0
        if diff > 180:
            self._direction = -1.0
            cmd_dir = "CCW"
        else:
            self._direction = 1.0
            cmd_dir = "CW"

        logger.debug(
            "Timed: slew to %.2f° (%s, %.1f°/s)",
            target_az, cmd_dir, self._deg_per_sec,
        )
        if self._serial:
            if isinstance(self._protocol, RelayProtocol):
                self._send(f"RELAY {cmd_dir}")
            else:
                cmd = self._protocol.move_to(target_az, speed)
                self._send(cmd)

    def abort(self) -> None:
        cmd = self._protocol.stop()
        self._send(cmd)
        with self._lock:
            self._slewing = False
            self._target = None
            self._direction = 0.0

    def update(self, dt: float) -> None:
        """Advance the virtual position based on elapsed time."""
        with self._lock:
            if not self._slewing or self._target is None:
                return
            target = self._target

            # Advance position
            self._position += self._direction * self._deg_per_sec * dt
            self._position %= 360.0

            # Check if we've arrived
            error = abs(target - self._position)
            if error > 180:
                error = 360 - error

            if error < self._deg_per_sec * dt + 0.5:
                self._position = target
                self._slewing = False
                self._target = None
                self._direction = 0.0
                logger.debug("Timed: target reached")
                # Stop the relay
                cmd = self._protocol.stop()
                self._send(cmd)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_driver(config: dict, serial_ctrl=None) -> DomeDriver:
    """Create the appropriate driver based on ``hardware.motor_type``.

    Supported values: ``stepper``, ``encoder``, ``timed`` (default).
    """
    motor_type = config.get("hardware", {}).get("motor_type", "stepper")
    motor_type = (motor_type or "stepper").lower().strip()

    if motor_type == "encoder":
        logger.info("Dome driver: Encoder (closed-loop)")
        return EncoderDriver(config, serial_ctrl)
    if motor_type == "timed":
        logger.info("Dome driver: Timed (dead reckoning)")
        return TimedDriver(config, serial_ctrl)

    logger.info("Dome driver: Stepper (open-loop)")
    return StepperDriver(config, serial_ctrl)
