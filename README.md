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
│   ├── main.py               # Main application entry point & controller
│   ├── gui.py                # Flet GUI (Dark Mode, Sci-Fi dashboard)
│   ├── ascom_handler.py      # ASCOM telescope communication
│   ├── vision.py             # ArUco marker detection and tracking
│   ├── serial_ctrl.py        # Arduino serial communication
│   ├── math_utils.py         # Azimuth calculations and vector math
│   ├── calibration.py        # GEM offset calibration solver
│   ├── dome_drivers.py       # Dome motor drivers (stepper/encoder/timed)
│   ├── alpaca_server.py      # ASCOM Alpaca REST server
│   ├── replay_handler.py     # Replay mode for recorded sessions
│   ├── data_loader.py        # Calibration CSV data loader
│   ├── settings_gui.py       # Settings dialog for config editing
│   ├── simulation_sensor.py  # Simulated dome sensor for testing
│   ├── voice.py              # Text-to-speech feedback
│   └── path_utils.py         # Portable base-path resolver
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
  serial_port: "COM3"       # Arduino port
  baud_rate: 9600
  timeout: 1.0
  motor_type: "stepper"     # stepper | encoder | timed
  protocol: "argus"         # argus | lesvedome | relay
  steps_per_degree: 100.0   # Stepper calibration
  ticks_per_degree: 50.0    # Encoder calibration
  degrees_per_second: 5.0   # Timed motor speed
  encoder_tolerance: 0.5    # Encoder deadband (degrees)
  homing:
    enabled: false
    azimuth: 0.0            # Home switch position (degrees)
    direction: "CW"         # Search direction: CW or CCW
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

### Control Loop Settings
```yaml
control:
  update_rate: 10                  # Hz
  drift_correction_enabled: true
  correction_threshold: 0.5        # degrees – minimum error before motor moves
  max_speed: 100                   # motor speed units (0-100)
```

### Safety Settings
```yaml
safety:
  telescope_protrudes: true        # true if the OTA extends into the dome slit
  safe_altitude: 90.0              # park altitude (°) before large dome rotations
  max_nudge_while_protruding: 2.0  # max dome correction (°) while telescope is in slit
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

- **main.py**: Integrates all components in a closed-loop control system (state machine, health monitoring, outlier rejection)
- **gui.py**: Dark-mode Sci-Fi dashboard built with Flet (telemetry, radar, status indicators, mode selector)
- **ascom_handler.py**: Handles all ASCOM telescope communication with auto-reconnect
- **vision.py**: Manages camera input and ArUco marker detection, including camera auto-discovery
- **serial_ctrl.py**: Controls Arduino via serial commands with auto-reconnect
- **math_utils.py**: Performs all astronomical and geometric calculations (RA/Dec → Alt/Az → dome azimuth)
- **calibration.py**: GEM offset solver using scipy least-squares optimisation
- **dome_drivers.py**: Hardware-agnostic dome driver layer (stepper, encoder, timed) with protocol translators (ARGUS native, LesveDome, relay)
- **alpaca_server.py**: ASCOM Alpaca REST server so observatory software (NINA, Voyager, …) can slave the dome
- **replay_handler.py**: Mock ASCOM handler that replays recorded telescope sessions for testing and demos
- **data_loader.py**: Loads calibration CSV files (semicolon and comma formats)
- **settings_gui.py**: Flet AlertDialog-based settings panel for editing config.yaml at runtime
- **simulation_sensor.py**: Simulated dome azimuth sensor for testing without hardware
- **voice.py**: Threaded text-to-speech announcements (pyttsx3)
- **path_utils.py**: Portable base-path resolver for frozen/EXE and development environments

### Key Features

- **Closed-loop control**: Vision feedback corrects mathematical predictions
- **GEM support**: Accounts for German Equatorial Mount geometry and offsets
- **Configurable**: All parameters adjustable via YAML configuration or the in-app settings dialog
- **Robust**: Handles component failures gracefully (operates with partial functionality)
- **Modular**: Each subsystem can be tested and developed independently
- **Collision avoidance**: Parks telescope before large dome rotations when the OTA protrudes into the slit
- **ASCOM Alpaca server**: Allows observatory automation software (NINA, Voyager, …) to control the dome

### Dome Driver Types

ARGUS supports three motor driver strategies via the `hardware.motor_type` setting:

| Type | Description |
|---|---|
| `stepper` | Open-loop stepper motor. Position is derived from a steps-per-degree calibration factor. |
| `encoder` | DC motor with encoder feedback (closed-loop). A configurable tolerance band prevents oscillation. |
| `timed` | Relay-driven motor without position sensor. Position is estimated via dead reckoning. |

### Communication Protocols

The `hardware.protocol` setting selects the wire format sent to the motor controller:

| Protocol | Description |
|---|---|
| `argus` | Native ARGUS protocol (`MOVE az speed`, `STOP`, `STATUS`, `HOME dir`) |
| `lesvedome` | LesveDome industry-standard command set (`G az`, `S`, `P`, `H`) |
| `relay` | Simple relay ON/OFF protocol for time-based motors |

### ASCOM Alpaca Server

When the Alpaca server module is available, ARGUS exposes itself as an ASCOM Alpaca Dome device on port **11111** (the Alpaca standard). Observatory automation tools like **NINA** or **Voyager** can connect to `http://<host>:11111/api/v1/dome/0/` and slave the dome without a native ASCOM driver.

## Arduino Protocol

The Arduino should respond to these commands (native ARGUS protocol):

- `MOVE <azimuth> <speed>`: Move to azimuth (0-360°) at specified speed (0-100)
- `STOP`: Emergency stop
- `STATUS`: Query current position and status
- `HOME <direction>`: Start a homing run (`CW` or `CCW`)

Example:
```
MOVE 180.50 50
STATUS
HOME CW
STOP
```

See [arduino_example/README.md](arduino_example/README.md) for the full firmware example and wiring details.

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

Contributions are subject to the proprietary license terms.
Please contact the author before submitting pull requests.
By contributing, you agree that your contributions become the
intellectual property of the project owner.

## Acknowledgments

- ASCOM Initiative for telescope control standards
- OpenCV for computer vision capabilities
- Astropy for astronomical calculations
