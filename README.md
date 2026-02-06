# ARGUS - Advanced Rotation Guidance Using Sensors

A.R.G.U.S. steuert Sternwarten-Kuppeln hybrid: Präzise Vektorberechnung der Montierungsdaten wird durch visuelles Kamera-Tracking korrigiert. Dieser Ansatz gleicht Geometrie-Offsets und mechanischen Schlupf in Echtzeit aus und garantiert dem Teleskop stets freie Sicht.

## Overview

ARGUS is a hybrid dome-slaving system designed for Windows that combines:

1. **ASCOM Integration**: Retrieves telescope data (RA/Dec/SideOfPier) via `win32com.client`
2. **Vision System**: Uses OpenCV to track ArUco markers on the dome slit for drift correction
3. **Mathematical Calculations**: Computes required dome azimuth using vector mathematics (NumPy/Astropy) with GEM offset support
4. **Hardware Control**: Sends motor commands to Arduino via `pyserial`

## Architecture

```
ARGUS/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Main application entry point
│   ├── gui.py                # customtkinter GUI (Dark Mode)
│   ├── ascom_handler.py      # ASCOM telescope communication
│   ├── vision.py             # ArUco marker detection and tracking
│   ├── serial_ctrl.py        # Arduino serial communication
│   ├── math_utils.py         # Azimuth calculations and vector math
│   ├── calibration.py        # GEM offset calibration solver
│   ├── settings_gui.py       # Settings window for config editing
│   ├── simulation_sensor.py  # Simulated dome sensor for testing
│   └── voice.py              # Text-to-speech feedback
├── docs/
│   ├── USER_MANUAL_EN.md     # User manual (English)
│   └── USER_MANUAL_DE.md     # Benutzerhandbuch (Deutsch)
├── tests/                    # Automated test suite
├── arduino_example/          # Example Arduino firmware
├── assets/themes/            # GUI colour themes
├── config.yaml               # Configuration file
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
└── README.md                 # This file
```

## Requirements

- **Operating System**: Windows (for ASCOM support)
- **Python**: 3.8 or higher
- **Hardware**:
  - ASCOM-compatible telescope mount
  - USB webcam
  - Arduino with motor controller
  - ArUco markers mounted on dome slit

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Neuroklast/ARGUS.git
   cd ARGUS
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install the package** (optional):
   ```bash
   pip install -e .
   ```

## Configuration

Edit `config.yaml` to configure your system:

### ASCOM Settings
```yaml
ascom:
  telescope_prog_id: "ASCOM.Simulator.Telescope"  # Your telescope driver
  poll_interval: 1.0
```

### Vision Settings
```yaml
vision:
  camera_index: 0  # USB camera index
  resolution:
    width: 1280
    height: 720
  aruco:
    dictionary: "DICT_4X4_50"
    marker_size: 0.05  # meters
```

### Hardware Settings
```yaml
hardware:
  serial_port: "COM3"  # Arduino port
  baud_rate: 9600
  timeout: 1.0
```

### Observatory Configuration
```yaml
math:
  observatory:
    latitude: 51.5074   # degrees
    longitude: -0.1278  # degrees
    elevation: 0        # meters
  dome:
    radius: 2.5         # meters
    slit_width: 0.8     # meters
  mount:
    pier_height: 1.5    # meters
    gem_offset_east: 0.0
    gem_offset_north: 0.0
```

## Usage

### Run ARGUS with default configuration:
```bash
python src/main.py
```

### Run with custom configuration:
```bash
python src/main.py --config /path/to/custom_config.yaml
```

### If installed as a package:
```bash
argus
argus --config /path/to/custom_config.yaml
```

## How It Works

1. **Telescope Tracking**: ARGUS continuously polls the ASCOM telescope for current RA/Dec coordinates and side of pier information.

2. **Mathematical Calculation**: The system converts telescope coordinates to Alt/Az, then calculates the required dome azimuth accounting for:
   - Observatory location
   - Dome geometry
   - Telescope pier position
   - GEM mount offsets

3. **Vision Correction**: A USB camera detects ArUco markers on the dome slit. Any drift from the expected position is measured and used to correct the calculated azimuth in real-time.

4. **Motor Control**: The corrected azimuth command is sent to the Arduino, which controls the dome motors to maintain proper alignment.

## Development

### Project Structure

- **ascom_handler.py**: Handles all ASCOM telescope communication
- **vision.py**: Manages camera input and ArUco marker detection
- **serial_ctrl.py**: Controls Arduino via serial commands
- **math_utils.py**: Performs all astronomical and geometric calculations
- **gui.py**: Dark-mode GUI built with customtkinter (telemetry, status, controls, mode selector)
- **main.py**: Integrates all components in a closed-loop control system

### Key Features

- **Closed-loop control**: Vision feedback corrects mathematical predictions
- **GEM support**: Accounts for German Equatorial Mount geometry and offsets
- **Configurable**: All parameters adjustable via YAML configuration
- **Robust**: Handles component failures gracefully (operates with partial functionality)
- **Modular**: Each subsystem can be tested and developed independently

## Arduino Protocol

The Arduino should respond to these commands:

- `MOVE <azimuth> <speed>`: Move to azimuth (0-360°) at specified speed (0-100)
- `STOP`: Emergency stop
- `STATUS`: Query current position and status

Example:
```
MOVE 180.50 50
STOP
STATUS
```

## Troubleshooting

### ASCOM Connection Issues
- Ensure ASCOM Platform is installed
- Verify telescope driver ProgID in config.yaml
- Check telescope is powered and connected

### Camera Not Found
- Verify camera is connected and recognized by Windows
- Try different camera_index values (0, 1, 2, etc.)
- Check camera permissions

### Serial Port Errors
- Verify Arduino is connected to the correct COM port
- Check Device Manager for COM port assignment
- Ensure no other application is using the port

### ArUco Markers Not Detected
- Ensure markers are properly printed and mounted
- Verify ArUco dictionary matches printed markers
- Check lighting conditions
- Adjust camera focus

## License

This software is proprietary. Copyright © 2026 Kay Schäfer. All Rights Reserved.
Governed by the laws of the Federal Republic of Germany.
See [LICENSE](LICENSE) for full terms.

Third-party open-source components are listed in
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

## Documentation

- **English User Manual**: [docs/USER_MANUAL_EN.md](docs/USER_MANUAL_EN.md)
- **Benutzerhandbuch (Deutsch)**: [docs/USER_MANUAL_DE.md](docs/USER_MANUAL_DE.md)

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Acknowledgments

- ASCOM Initiative for telescope control standards
- OpenCV for computer vision capabilities
- Astropy for astronomical calculations
