"""
ARGUS - Advanced Rotation Guidance Using Sensors
Package initialization

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.
"""

__version__ = "0.1.0"
__author__ = "ARGUS Development Team"
__description__ = "Hybrid dome-slaving system with vision-based drift correction"

from .ascom_handler import ASCOMHandler
from .vision import VisionSystem
from .serial_ctrl import SerialController
from .math_utils import MathUtils
from .gui import ArgusApp
from .simulation_sensor import SimulationSensor

__all__ = [
    'ASCOMHandler',
    'VisionSystem',
    'SerialController',
    'MathUtils',
    'ArgusApp',
    'SimulationSensor',
]
