"""
ARGUS - Advanced Rotation Guidance Using Sensors
Main Application Entry Point

This is the main control loop that integrates:
1. ASCOM telescope communication
2. Vision-based ArUco marker tracking
3. Mathematical azimuth calculations
4. Serial motor control
"""

import logging
import yaml
import time
import sys
from pathlib import Path
from typing import Dict, Optional

try:
    import coloredlogs
    COLOREDLOGS_AVAILABLE = True
except ImportError:
    COLOREDLOGS_AVAILABLE = False

from ascom_handler import ASCOMHandler
from vision import VisionSystem
from serial_ctrl import SerialController
from math_utils import MathUtils


class ARGUS:
    """Main ARGUS application controller."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize ARGUS system.
        
        Args:
            config_path: Path to configuration file
        """
        # Setup logging first
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("=" * 60)
        self.logger.info("ARGUS - Advanced Rotation Guidance Using Sensors")
        self.logger.info("=" * 60)
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Initialize components (lazy initialization)
        self.ascom = None
        self.vision = None
        self.serial = None
        self.math = None
        
        self.running = False
    
    def setup_logging(self) -> None:
        """Setup logging configuration."""
        # Default to INFO level
        log_level = logging.INFO
        
        if COLOREDLOGS_AVAILABLE:
            coloredlogs.install(
                level=log_level,
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def load_config(self, config_path: str) -> Dict:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to config file
            
        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing configuration: {e}")
            sys.exit(1)
    
    def initialize_components(self) -> bool:
        """
        Initialize all ARGUS components.
        
        Returns:
            True if all components initialized successfully
        """
        self.logger.info("Initializing ARGUS components...")
        
        try:
            # Initialize Math utilities
            self.logger.info("Initializing mathematical utilities...")
            self.math = MathUtils(
                latitude=self.config['math']['observatory']['latitude'],
                longitude=self.config['math']['observatory']['longitude'],
                elevation=self.config['math']['observatory']['elevation'],
                dome_radius=self.config['math']['dome']['radius'],
                pier_height=self.config['math']['mount']['pier_height'],
                gem_offset_east=self.config['math']['mount']['gem_offset_east'],
                gem_offset_north=self.config['math']['mount']['gem_offset_north']
            )
            
            # Initialize ASCOM handler
            self.logger.info("Initializing ASCOM handler...")
            try:
                self.ascom = ASCOMHandler(
                    self.config['ascom']['telescope_prog_id']
                )
                if not self.ascom.connect():
                    self.logger.warning("ASCOM connection failed - continuing without telescope")
                    self.ascom = None
            except RuntimeError as e:
                self.logger.warning(f"ASCOM not available: {e}")
                self.ascom = None
            
            # Initialize Vision system
            self.logger.info("Initializing vision system...")
            self.vision = VisionSystem(
                camera_index=self.config['vision']['camera_index'],
                resolution=(
                    self.config['vision']['resolution']['width'],
                    self.config['vision']['resolution']['height']
                ),
                aruco_dict=self.config['vision']['aruco']['dictionary'],
                marker_size=self.config['vision']['aruco']['marker_size']
            )
            if not self.vision.open_camera():
                self.logger.warning("Camera initialization failed - continuing without vision")
                self.vision = None
            
            # Initialize Serial controller
            self.logger.info("Initializing serial controller...")
            try:
                self.serial = SerialController(
                    port=self.config['hardware']['serial_port'],
                    baud_rate=self.config['hardware']['baud_rate'],
                    timeout=self.config['hardware']['timeout']
                )
                if not self.serial.connect():
                    self.logger.warning("Serial connection failed - continuing without motor control")
                    self.serial = None
            except Exception as e:
                self.logger.warning(f"Serial initialization failed: {e}")
                self.serial = None
            
            self.logger.info("Component initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False
    
    def shutdown_components(self) -> None:
        """Shutdown all components gracefully."""
        self.logger.info("Shutting down ARGUS components...")
        
        if self.ascom:
            self.ascom.disconnect()
        
        if self.vision:
            self.vision.close_camera()
        
        if self.serial:
            self.serial.stop_motor()
            self.serial.disconnect()
        
        self.logger.info("All components shut down")
    
    def control_loop(self) -> None:
        """Main control loop."""
        self.logger.info("Starting ARGUS control loop")
        self.running = True
        
        update_interval = 1.0 / self.config['control']['update_rate']
        drift_correction_enabled = self.config['control']['drift_correction_enabled']
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Get telescope position
                if self.ascom:
                    telescope_data = self.ascom.get_all_data()
                    if telescope_data:
                        ra = telescope_data['ra']
                        dec = telescope_data['dec']
                        side_of_pier = telescope_data['side_of_pier']
                        
                        # Calculate required dome azimuth
                        target_azimuth = self.math.calculate_required_azimuth(
                            ra, dec, side_of_pier
                        )
                        
                        # Apply drift correction if vision is available
                        if self.vision and drift_correction_enabled:
                            frame = self.vision.capture_frame()
                            if frame is not None:
                                marker_data = self.vision.detect_markers(frame)
                                if marker_data:
                                    # Calculate drift from frame center
                                    frame_center = (
                                        frame.shape[1] / 2,
                                        frame.shape[0] / 2
                                    )
                                    drift = self.vision.calculate_drift(
                                        marker_data, frame_center
                                    )
                                    if drift:
                                        target_azimuth = self.math.apply_drift_correction(
                                            target_azimuth, drift
                                        )
                        
                        # Send command to dome
                        if self.serial:
                            self.serial.move_to_azimuth(
                                target_azimuth,
                                self.config['control']['max_speed']
                            )
                            self.logger.info(
                                f"Target azimuth: {target_azimuth:.2f}° "
                                f"(RA={ra:.4f}h, Dec={dec:.2f}°)"
                            )
                
                # Maintain update rate
                elapsed = time.time() - loop_start
                if elapsed < update_interval:
                    time.sleep(update_interval - elapsed)
                    
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Error in control loop: {e}", exc_info=True)
        finally:
            self.running = False
    
    def run(self) -> None:
        """Run the ARGUS system."""
        if not self.initialize_components():
            self.logger.error("Failed to initialize - exiting")
            return
        
        try:
            self.control_loop()
        finally:
            self.shutdown_components()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ARGUS - Advanced Rotation Guidance Using Sensors'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    args = parser.parse_args()
    
    # Create and run ARGUS
    argus = ARGUS(config_path=args.config)
    argus.run()


if __name__ == '__main__':
    main()
