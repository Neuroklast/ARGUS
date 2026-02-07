"""
ARGUS - Advanced Rotation Guidance Using Sensors
Mathematical Utilities Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

This module provides vector mathematics for azimuth calculations
including GEM (German Equatorial Mount) offset corrections.
"""

import logging
import time
import numpy as np
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u
from typing import Tuple, Dict, Optional


class MathUtils:
    """Mathematical utilities for dome positioning calculations."""
    
    def __init__(self, latitude: float, longitude: float, elevation: float,
                 dome_radius: float, pier_height: float,
                 gem_offset_east: float = 0.0, gem_offset_north: float = 0.0,
                 latency_compensation_ms: float = 0.0):
        """
        Initialize mathematical utilities.
        
        Args:
            latitude: Observatory latitude in degrees
            longitude: Observatory longitude in degrees
            elevation: Observatory elevation in meters
            dome_radius: Dome radius in meters
            pier_height: Telescope pier height in meters
            gem_offset_east: GEM offset in east direction (meters)
            gem_offset_north: GEM offset in north direction (meters)
            latency_compensation_ms: Look-ahead time in milliseconds for
                predictive dome slaving.  When > 0 the dome target azimuth
                is extrapolated based on the current telescope slew velocity
                so that the slit is already at the correct position when
                the telescope arrives.
        """
        self.logger = logging.getLogger(__name__)
        
        # Observatory location
        self.location = EarthLocation(
            lat=latitude * u.deg,
            lon=longitude * u.deg,
            height=elevation * u.m
        )
        
        # Dome geometry
        self.dome_radius = dome_radius
        self.pier_height = pier_height
        self.gem_offset_east = gem_offset_east
        self.gem_offset_north = gem_offset_north
        
        # Predictive slaving (look-ahead)
        self.latency_compensation_ms = max(0.0, latency_compensation_ms)
        self._prev_azimuth: Optional[float] = None
        self._prev_time: Optional[float] = None
        
        self.logger.info(
            "MathUtils initialized: lat=%s, lon=%s, "
            "dome_r=%sm, pier_h=%sm, look_ahead=%sms",
            latitude, longitude, dome_radius, pier_height,
            latency_compensation_ms,
        )
    
    def ra_dec_to_altaz(self, ra: float, dec: float, 
                        obstime: Optional[Time] = None) -> Tuple[float, float]:
        """
        Convert RA/Dec to Altitude/Azimuth.
        
        Args:
            ra: Right Ascension in hours
            dec: Declination in degrees
            obstime: Observation time (defaults to now)
            
        Returns:
            Tuple of (altitude, azimuth) in degrees
        """
        if obstime is None:
            obstime = Time.now()
        
        # Create sky coordinate
        coord = SkyCoord(
            ra=ra * u.hourangle,
            dec=dec * u.deg,
            frame='icrs'
        )
        
        # Transform to AltAz frame
        altaz_frame = AltAz(obstime=obstime, location=self.location)
        altaz = coord.transform_to(altaz_frame)
        
        return (altaz.alt.degree, altaz.az.degree)
    
    def calculate_telescope_vector(self, altitude: float, azimuth: float,
                                   side_of_pier: Optional[int] = None) -> np.ndarray:
        """
        Calculate telescope pointing vector including GEM offset.
        
        Args:
            altitude: Telescope altitude in degrees
            azimuth: Telescope azimuth in degrees
            side_of_pier: 0=East, 1=West (None if not applicable)
            
        Returns:
            3D vector [x, y, z] in meters from dome center
        """
        # Convert to radians
        alt_rad = np.radians(altitude)
        az_rad = np.radians(azimuth)
        
        # Base telescope position (on pier)
        # Coordinate system: x=East, y=North, z=Up
        base_x = self.gem_offset_east
        base_y = self.gem_offset_north
        base_z = self.pier_height
        
        # Calculate unit vector in pointing direction
        # Standard spherical to cartesian conversion
        pointing_x = np.cos(alt_rad) * np.sin(az_rad)
        pointing_y = np.cos(alt_rad) * np.cos(az_rad)
        pointing_z = np.sin(alt_rad)
        
        # Apply GEM-specific offsets if side of pier is known
        if side_of_pier is not None:
            # When telescope is on East side (pointing West), slight offset
            # When telescope is on West side (pointing East), opposite offset
            if side_of_pier == 0:  # pierEast
                base_x += 0.1  # Small eastward offset
            elif side_of_pier == 1:  # pierWest
                base_x -= 0.1  # Small westward offset
        
        # Telescope optical axis vector from dome center
        telescope_vec = np.array([
            base_x + pointing_x,
            base_y + pointing_y,
            base_z + pointing_z
        ])
        
        return telescope_vec
    
    def calculate_dome_azimuth(self, telescope_vector: np.ndarray) -> float:
        """
        Calculate required dome azimuth from telescope vector.
        
        Args:
            telescope_vector: 3D telescope pointing vector
            
        Returns:
            Required dome azimuth in degrees (0-360)
        """
        # Project onto horizontal plane (x-y)
        x, y, z = telescope_vector
        
        # Calculate azimuth from North (0°) clockwise
        azimuth_rad = np.arctan2(x, y)
        azimuth_deg = np.degrees(azimuth_rad)
        
        # Normalize to 0-360
        if azimuth_deg < 0:
            azimuth_deg += 360
        
        return azimuth_deg
    
    def calculate_required_azimuth(self, ra: float, dec: float,
                                   side_of_pier: Optional[int] = None,
                                   obstime: Optional['Time'] = None) -> float:
        """
        Calculate required dome azimuth from telescope coordinates.
        
        Args:
            ra: Right Ascension in hours
            dec: Declination in degrees
            side_of_pier: Side of pier (0=East, 1=West)
            obstime: Observation time (defaults to now)
            
        Returns:
            Required dome azimuth in degrees
        """
        # Convert RA/Dec to Alt/Az
        altitude, azimuth = self.ra_dec_to_altaz(ra, dec, obstime=obstime)
        
        # Calculate telescope vector with GEM offset
        telescope_vec = self.calculate_telescope_vector(
            altitude, azimuth, side_of_pier
        )
        
        # Calculate dome azimuth
        dome_azimuth = self.calculate_dome_azimuth(telescope_vec)
        
        self.logger.debug(
            "RA=%sh, Dec=%s°, Alt=%.2f°, Az=%.2f° -> Dome Az=%.2f°",
            ra, dec, altitude, azimuth, dome_azimuth,
        )
        
        return dome_azimuth

    def extrapolate_azimuth(self, current_azimuth: float) -> float:
        """Apply linear look-ahead extrapolation to compensate for latency.

        Estimates the telescope's angular velocity from consecutive calls
        and adds ``latency_compensation_ms`` worth of predicted motion to
        the target azimuth.  This prevents the dome slit from lagging
        behind during fast slews (satellite tracking) or when the
        communication chain introduces noticeable delay.

        Args:
            current_azimuth: The dome target azimuth calculated from the
                current telescope position (degrees, 0-360).

        Returns:
            Extrapolated dome azimuth in degrees (0-360).  When
            ``latency_compensation_ms`` is 0 or there is not enough
            history, *current_azimuth* is returned unchanged.
        """
        if self.latency_compensation_ms <= 0:
            return current_azimuth

        now = time.time()

        if self._prev_azimuth is None or self._prev_time is None:
            self._prev_azimuth = current_azimuth
            self._prev_time = now
            return current_azimuth

        dt = now - self._prev_time
        if dt < 1e-6:
            return current_azimuth

        # Angular velocity (degrees/second), wrapped to ±180°
        delta = current_azimuth - self._prev_azimuth
        if delta > 180:
            delta -= 360
        elif delta < -180:
            delta += 360

        velocity = delta / dt  # deg/s

        # Extrapolate
        look_ahead_s = self.latency_compensation_ms / 1000.0
        predicted = current_azimuth + velocity * look_ahead_s

        # Normalise to 0-360
        predicted = predicted % 360.0

        self.logger.debug(
            "Look-ahead: vel=%.2f°/s, dt=%.3fs, "
            "current=%.2f° -> predicted=%.2f°",
            velocity, dt, current_azimuth, predicted,
        )

        self._prev_azimuth = current_azimuth
        self._prev_time = now
        return predicted

    def apply_drift_correction(self, target_azimuth: float, 
                               drift_pixels: Tuple[float, float],
                               pixels_per_degree: float = 10.0) -> float:
        """
        Apply drift correction from vision system.
        
        Args:
            target_azimuth: Calculated target azimuth
            drift_pixels: (dx, dy) drift in pixels
            pixels_per_degree: Camera calibration factor
            
        Returns:
            Corrected azimuth in degrees
        """
        # Convert pixel drift to angular drift
        dx, dy = drift_pixels
        
        # Horizontal drift corresponds to azimuth correction
        angular_drift = dx / pixels_per_degree
        
        # Apply correction
        corrected_azimuth = (target_azimuth + angular_drift) % 360
        
        self.logger.debug(
            "Drift correction: %.3f° (%.2f° -> %.2f°)",
            angular_drift, target_azimuth, corrected_azimuth,
        )
        
        return corrected_azimuth
