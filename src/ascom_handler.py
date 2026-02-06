"""
ARGUS - Advanced Rotation Guidance Using Sensors
ASCOM Telescope Handler Module

This module provides communication with ASCOM-compatible telescopes
using win32com.client to retrieve telescope data (RA, Dec, SideOfPier).
Includes automatic reconnection on COM errors.
"""

import logging
import time
from typing import Dict, Optional, Tuple

try:
    import win32com.client
    ASCOM_AVAILABLE = True
except ImportError:
    ASCOM_AVAILABLE = False
    logging.warning("win32com not available - ASCOM functionality disabled")


class ASCOMHandler:
    """Handler for ASCOM telescope communication with auto-reconnect."""

    RECONNECT_DELAY = 5.0  # seconds between reconnect attempts

    def __init__(self, prog_id: str):
        """
        Initialize ASCOM telescope connection.

        Args:
            prog_id: ASCOM ProgID for the telescope driver
        """
        self.logger = logging.getLogger(__name__)
        self.prog_id = prog_id
        self.telescope = None
        self.connected = False
        self._last_reconnect_attempt = 0.0

        if not ASCOM_AVAILABLE:
            raise RuntimeError("win32com not available - cannot use ASCOM")

    def connect(self) -> bool:
        """
        Connect to the ASCOM telescope.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to ASCOM telescope: {self.prog_id}")
            self.telescope = win32com.client.Dispatch(self.prog_id)
            self.telescope.Connected = True
            self.connected = True
            self.logger.info("ASCOM telescope connected successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to ASCOM telescope: {e}")
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the ASCOM telescope."""
        if self.telescope and self.connected:
            try:
                self.telescope.Connected = False
                self.connected = False
                self.logger.info("ASCOM telescope disconnected")
            except Exception as e:
                self.logger.error(f"Error disconnecting telescope: {e}")

    def _attempt_reconnect(self) -> bool:
        """Try to re-establish the ASCOM connection with backoff.

        Returns:
            True if reconnection succeeded, False otherwise.
        """
        now = time.time()
        if now - self._last_reconnect_attempt < self.RECONNECT_DELAY:
            return False
        self._last_reconnect_attempt = now

        self.logger.warning("Attempting ASCOM reconnect for %s …", self.prog_id)
        return self.connect()

    def get_position(self) -> Optional[Dict[str, float]]:
        """
        Get current telescope position.

        Returns:
            Dictionary with RA, Dec, Altitude, Azimuth or None if error
        """
        if not self.connected:
            self.logger.warning("Telescope not connected")
            return None

        try:
            ra = self.telescope.RightAscension  # hours
            dec = self.telescope.Declination  # degrees
            alt = self.telescope.Altitude  # degrees
            az = self.telescope.Azimuth  # degrees

            return {
                'ra': ra,
                'dec': dec,
                'altitude': alt,
                'azimuth': az
            }
        except Exception as e:
            self.logger.error(f"Error getting telescope position: {e}")
            self.connected = False
            if self._attempt_reconnect():
                return self.get_position()
            self.logger.critical("ASCOM reconnect failed – position unavailable")
            return None

    def get_side_of_pier(self) -> Optional[int]:
        """
        Get the side of pier for German Equatorial Mounts.

        Returns:
            0 = pierEast (pointing West)
            1 = pierWest (pointing East)
            None if error or not applicable
        """
        if not self.connected:
            self.logger.warning("Telescope not connected")
            return None

        try:
            # Check if telescope supports SideOfPier
            if hasattr(self.telescope, 'SideOfPier'):
                return self.telescope.SideOfPier
            else:
                self.logger.warning("Telescope does not support SideOfPier")
                return None
        except Exception as e:
            self.logger.error(f"Error getting SideOfPier: {e}")
            self.connected = False
            self._attempt_reconnect()
            return None

    def get_tracking_state(self) -> bool:
        """
        Get telescope tracking state.

        Returns:
            True if tracking, False otherwise
        """
        if not self.connected:
            return False

        try:
            return self.telescope.Tracking
        except Exception as e:
            self.logger.error(f"Error getting tracking state: {e}")
            self.connected = False
            self._attempt_reconnect()
            return False

    def get_all_data(self) -> Optional[Dict]:
        """
        Get all relevant telescope data.

        Returns:
            Dictionary with all telescope data or None if error
        """
        position = self.get_position()
        if position is None:
            return None

        side_of_pier = self.get_side_of_pier()
        tracking = self.get_tracking_state()

        return {
            **position,
            'side_of_pier': side_of_pier,
            'tracking': tracking
        }
