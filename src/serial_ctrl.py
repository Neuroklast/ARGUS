"""
ARGUS - Advanced Rotation Guidance Using Sensors
Serial Control Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

This module handles communication with Arduino for motor control
via pyserial.  Includes automatic reconnection on IO errors.
"""

import logging
import serial
import time
from typing import Optional


class SerialController:
    """Controller for Arduino serial communication with auto-reconnect."""

    RECONNECT_DELAY = 5.0  # seconds between reconnect attempts

    def __init__(self, port: str, baud_rate: int = 9600, timeout: float = 1.0):
        """
        Initialize serial controller.

        Args:
            port: Serial port name (e.g., 'COM3' on Windows)
            baud_rate: Communication baud rate
            timeout: Read timeout in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None
        self.connected = False
        self._last_reconnect_attempt = 0.0

    def connect(self) -> bool:
        """
        Connect to the serial port.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Connecting to serial port %s", self.port)
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout
            )

            # Wait for Arduino to reset
            time.sleep(2)

            self.connected = True
            self.logger.info("Serial port %s connected successfully", self.port)
            return True
        except serial.SerialException as e:
            self.logger.error("Failed to connect to serial port: %s", e)
            self.connected = False
            return False
        except Exception as e:
            self.logger.error("Unexpected error connecting to serial port: %s", e)
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the serial port."""
        if self.ser and self.connected:
            try:
                self.ser.close()
                self.connected = False
                self.logger.info("Serial port disconnected")
            except Exception as e:
                self.logger.error("Error disconnecting serial port: %s", e)

    def _attempt_reconnect(self) -> bool:
        """Try to re-establish the serial connection with backoff.

        Returns:
            True if reconnection succeeded, False otherwise.
        """
        now = time.time()
        if now - self._last_reconnect_attempt < self.RECONNECT_DELAY:
            return False
        self._last_reconnect_attempt = now

        self.logger.warning("Attempting serial reconnect on %s …", self.port)
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        return self.connect()

    def send_command(self, command: str) -> bool:
        """
        Send a command to the Arduino.

        Args:
            command: Command string to send

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.logger.warning("Serial port not connected")
            return False

        try:
            # Ensure command ends with newline
            if not command.endswith('\n'):
                command += '\n'

            self.ser.write(command.encode('utf-8'))
            self.logger.debug("Sent command: %s", command.strip())
            return True
        except serial.SerialException as e:
            self.logger.error("Serial IO error sending command: %s", e)
            self.connected = False
            if self._attempt_reconnect():
                return self.send_command(command)
            self.logger.critical("Serial reconnect failed – command lost")
            return False
        except Exception as e:
            self.logger.error("Error sending command: %s", e)
            return False

    def read_response(self, max_lines: int = 1) -> Optional[str]:
        """
        Read response from Arduino.

        Args:
            max_lines: Maximum number of lines to read

        Returns:
            Response string or None if error
        """
        if not self.connected:
            self.logger.warning("Serial port not connected")
            return None

        try:
            lines = []
            for _ in range(max_lines):
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        lines.append(line)

            if lines:
                response = '\n'.join(lines)
                self.logger.debug("Received response: %s", response)
                return response
            return None
        except serial.SerialException as e:
            self.logger.error("Serial IO error reading response: %s", e)
            self.connected = False
            self._attempt_reconnect()
            return None
        except Exception as e:
            self.logger.error("Error reading response: %s", e)
            return None

    def send_and_receive(self, command: str, timeout: float = 1.0) -> Optional[str]:
        """
        Send command and wait for response.

        Args:
            command: Command to send
            timeout: Time to wait for response

        Returns:
            Response string or None if error
        """
        if not self.send_command(command):
            return None

        time.sleep(timeout)
        return self.read_response()

    def move_to_azimuth(self, azimuth: float, speed: int = 50) -> bool:
        """
        Send command to move dome to specific azimuth.

        Args:
            azimuth: Target azimuth in degrees (0-360)
            speed: Motor speed (0-100)

        Returns:
            True if command sent successfully
        """
        # Validate inputs
        azimuth = azimuth % 360
        speed = max(0, min(100, speed))

        command = f"MOVE {azimuth:.2f} {speed}"
        return self.send_command(command)

    def stop_motor(self) -> bool:
        """
        Send emergency stop command.

        Returns:
            True if command sent successfully
        """
        return self.send_command("STOP")

    def get_status(self) -> Optional[str]:
        """
        Query current dome status.

        Returns:
            Status string or None if error
        """
        return self.send_and_receive("STATUS")

    def send_ping(self) -> bool:
        """Send a heartbeat PING to the Arduino watchdog.

        The firmware resets its watchdog timer on every received command.
        This dedicated PING command is lightweight and should be called
        periodically (e.g. every 10-30 s) to prevent the watchdog from
        closing the shutter.

        Returns:
            True if the command was sent successfully.
        """
        return self.send_command("PING")
