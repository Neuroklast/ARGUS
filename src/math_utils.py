"""
ARGUS - Advanced Rotation Guidance Using Sensors
Mathematical Utilities Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

This module provides vector mathematics for azimuth calculations
including GEM (German Equatorial Mount) offset corrections.
"""

import logging
import numpy as np
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u
from typing import Tuple, Dict, Optional


class MathUtils:
    """Mathematical utilities for dome positioning calculations."""
    
    def __init__(self, latitude: float, longitude: float, elevation: float,
                 dome_radius: float, pier_height: float,
                 gem_offset_east: float = 0.0, gem_offset_north: float = 0.0):
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
        
        self.logger.info(
            f"MathUtils initialized: lat={latitude}, lon={longitude}, "
            f"dome_r={dome_radius}m, pier_h={pier_height}m"
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
                                   side_of_pier: Optional[int] = None) -> float:
        """
        Calculate required dome azimuth from telescope coordinates.
        
        Args:
            ra: Right Ascension in hours
            dec: Declination in degrees
            side_of_pier: Side of pier (0=East, 1=West)
            
        Returns:
            Required dome azimuth in degrees
        """
        # Convert RA/Dec to Alt/Az
        altitude, azimuth = self.ra_dec_to_altaz(ra, dec)
        
        # Calculate telescope vector with GEM offset
        telescope_vec = self.calculate_telescope_vector(
            altitude, azimuth, side_of_pier
        )
        
        # Calculate dome azimuth
        dome_azimuth = self.calculate_dome_azimuth(telescope_vec)
        
        self.logger.debug(
            f"RA={ra}h, Dec={dec}°, Alt={altitude:.2f}°, Az={azimuth:.2f}° "
            f"-> Dome Az={dome_azimuth:.2f}°"
        )
        
        return dome_azimuth
    
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
            f"Drift correction: {angular_drift:.3f}° "
            f"({target_azimuth:.2f}° -> {corrected_azimuth:.2f}°)"
        )
        
        return corrected_azimuth
