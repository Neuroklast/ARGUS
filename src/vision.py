"""
ARGUS - Advanced Rotation Guidance Using Sensors
Vision Processing Module

This module handles USB webcam input and ArUco marker detection
for drift correction in the dome slaving system.
"""

import logging
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict


class VisionSystem:
    """Vision system for ArUco marker detection and tracking."""
    
    # ArUco dictionary mappings
    ARUCO_DICTS = {
        "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
        "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
        "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
        "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
        "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
        "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
        "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
        "DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
        "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
        "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
        "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
        "DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
    }
    
    def __init__(self, camera_index: int, resolution: Tuple[int, int],
                 aruco_dict: str, marker_size: float):
        """
        Initialize vision system.
        
        Args:
            camera_index: USB camera index
            resolution: Tuple of (width, height)
            aruco_dict: ArUco dictionary name
            marker_size: Physical marker size in meters
        """
        self.logger = logging.getLogger(__name__)
        self.camera_index = camera_index
        self.resolution = resolution
        self.marker_size = marker_size
        
        # Initialize camera
        self.cap = None
        self.camera_open = False
        
        # Initialize ArUco detector
        if aruco_dict not in self.ARUCO_DICTS:
            raise ValueError(f"Unknown ArUco dictionary: {aruco_dict}")
        
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(
            self.ARUCO_DICTS[aruco_dict]
        )
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        self.logger.info(f"Vision system initialized with {aruco_dict}")
    
    def open_camera(self) -> bool:
        """
        Open the USB camera.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.logger.error(f"Failed to open camera {self.camera_index}")
                return False
            
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            
            self.camera_open = True
            self.logger.info(f"Camera {self.camera_index} opened successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error opening camera: {e}")
            return False
    
    def close_camera(self) -> None:
        """Close the camera."""
        if self.cap is not None:
            self.cap.release()
            self.camera_open = False
            self.logger.info("Camera closed")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from the camera.
        
        Returns:
            Frame as numpy array or None if error
        """
        if not self.camera_open:
            self.logger.warning("Camera not open")
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            self.logger.warning("Failed to capture frame")
            return None
        
        return frame
    
    def detect_markers(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Detect ArUco markers in a frame.
        
        Args:
            frame: Input image frame
            
        Returns:
            Dictionary with marker data or None if no markers found
        """
        try:
            # Convert to grayscale for better detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect markers
            corners, ids, rejected = self.detector.detectMarkers(gray)
            
            if ids is None or len(ids) == 0:
                return None
            
            # Calculate marker centers
            markers = []
            for i, marker_id in enumerate(ids):
                corner_points = corners[i][0]
                center_x = np.mean(corner_points[:, 0])
                center_y = np.mean(corner_points[:, 1])
                
                markers.append({
                    'id': int(marker_id[0]),
                    'center': (center_x, center_y),
                    'corners': corner_points
                })
            
            return {
                'count': len(markers),
                'markers': markers,
                'frame_shape': frame.shape
            }
        except Exception as e:
            self.logger.error(f"Error detecting markers: {e}")
            return None
    
    def calculate_drift(self, marker_data: Dict, expected_center: Tuple[float, float]) -> Optional[Tuple[float, float]]:
        """
        Calculate drift from expected marker position.
        
        Args:
            marker_data: Marker detection data
            expected_center: Expected (x, y) center position
            
        Returns:
            Tuple of (dx, dy) drift in pixels or None if error
        """
        if marker_data is None or marker_data['count'] == 0:
            return None
        
        # Use first marker for drift calculation
        marker = marker_data['markers'][0]
        actual_center = marker['center']
        
        dx = actual_center[0] - expected_center[0]
        dy = actual_center[1] - expected_center[1]
        
        return (dx, dy)
    
    def draw_markers(self, frame: np.ndarray, marker_data: Dict) -> np.ndarray:
        """
        Draw detected markers on frame for visualization.
        
        Args:
            frame: Input frame
            marker_data: Marker detection data
            
        Returns:
            Frame with drawn markers
        """
        if marker_data is None:
            return frame
        
        output = frame.copy()
        
        for marker in marker_data['markers']:
            # Draw marker boundaries
            corners = marker['corners'].astype(int)
            cv2.polylines(output, [corners], True, (0, 255, 0), 2)
            
            # Draw marker ID
            center = tuple(map(int, marker['center']))
            cv2.putText(output, f"ID: {marker['id']}", center,
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return output

    # ---- Camera auto-discovery ------------------------------------------
    @classmethod
    def find_working_camera(cls, max_indices: int = 5) -> Optional[int]:
        """Scan camera indices and return the first working one.

        Prioritises a camera where an ArUco marker is immediately detected.

        Args:
            max_indices: Number of indices to probe (0 … max_indices-1).

        Returns:
            Camera index of a working camera, or ``None``.
        """
        logger = logging.getLogger(__name__)
        first_working: Optional[int] = None

        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        params = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, params)

        for idx in range(max_indices):
            cap = cv2.VideoCapture(idx)
            if not cap.isOpened():
                cap.release()
                continue
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                continue

            if first_working is None:
                first_working = idx

            # Try ArUco detection – prefer cameras that immediately see a marker
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                corners, ids, _ = detector.detectMarkers(gray)
                if ids is not None and len(ids) > 0:
                    logger.info("Camera %d has ArUco marker – preferred", idx)
                    return idx
            except Exception:
                pass

        if first_working is not None:
            logger.info("Using first working camera at index %d", first_working)
        return first_working
