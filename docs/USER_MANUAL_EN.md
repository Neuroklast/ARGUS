# ARGUS User Manual

**Advanced Rotation Guidance Using Sensors**

Version 0.1.0

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation](#3-installation)
4. [Configuration](#4-configuration)
5. [Starting ARGUS](#5-starting-argus)
6. [User Interface](#6-user-interface)
7. [Operating Modes](#7-operating-modes)
8. [Calibration](#8-calibration)
9. [Dome Drivers & Protocols](#9-dome-drivers--protocols)
10. [ASCOM Alpaca Server](#10-ascom-alpaca-server)
11. [Replay / Demo Mode](#11-replay--demo-mode)
12. [Troubleshooting](#12-troubleshooting)
13. [Safety Notes](#13-safety-notes)

---

## 1. Introduction

ARGUS is a hybrid dome-slaving system for observatory telescope domes. It
combines mathematical calculation of the required dome azimuth with real-time
vision feedback from ArUco markers mounted on the dome slit.

**Key features:**

- ASCOM integration for telescope tracking data (RA/Dec/SideOfPier)
- OpenCV-based ArUco marker detection for drift correction
- Automatic GEM (German Equatorial Mount) offset support
- Arduino motor control via serial communication
- Dark-mode GUI with telemetry, radar view, and voice feedback
- Automatic hardware discovery and graceful degradation

## 2. System Requirements

### Hardware

| Component | Requirement |
|---|---|
| Operating system | Windows 10 or later |
| Telescope mount | ASCOM-compatible |
| Camera | USB webcam |
| Motor controller | Arduino with serial interface |
| Dome slit markers | Printed ArUco markers (DICT_4X4_50 by default) |

### Software

| Component | Version |
|---|---|
| Python | 3.8 or later |
| ASCOM Platform | 6.x or later |
| Arduino IDE | For uploading firmware (optional) |

## 3. Installation

### 3.1 Clone the Repository

```bash
git clone https://github.com/Neuroklast/ARGUS.git
cd ARGUS
```

### 3.2 Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3.3 Install as a Package (optional)

```bash
pip install -e .
```

### 3.4 Arduino Firmware

Upload the example sketch from `arduino_example/dome_controller.ino` to your
Arduino board using the Arduino IDE. Adjust pin assignments to match your motor
controller hardware.

### 3.5 Print ArUco Markers

Print at least one ArUco marker from the DICT_4X4_50 dictionary and mount it
on the dome slit edge so it is visible to the USB camera.

## 4. Configuration

All settings are stored in `config.yaml` in the project root.

### 4.1 ASCOM Settings

```yaml
ascom:
  telescope_prog_id: "ASCOM.Simulator.Telescope"
  poll_interval: 1.0
```

- **telescope_prog_id**: The ASCOM ProgID of your telescope driver. On first
  start, ARGUS will open the ASCOM Chooser dialog if the default simulator is
  still configured.
- **poll_interval**: How often telescope data is read (seconds).

### 4.2 Vision Settings

```yaml
vision:
  camera_index: 0
  resolution:
    width: 1280
    height: 720
  aruco:
    dictionary: "DICT_4X4_50"
    marker_size: 0.05
```

- **camera_index**: The USB camera index (0 is usually the first camera).
  ARGUS will auto-discover a working camera if the configured index fails.
- **marker_size**: Physical size of the ArUco marker in metres.

### 4.3 Hardware Settings

```yaml
hardware:
  serial_port: "COM3"
  baud_rate: 9600
  timeout: 1.0
```

- **serial_port**: The COM port of the Arduino.
- **baud_rate**: Must match the Arduino firmware setting.

### 4.4 Observatory Geometry

```yaml
math:
  observatory:
    latitude: 51.5074
    longitude: -0.1278
    elevation: 0
  dome:
    radius: 2.5
    slit_width: 0.8
  mount:
    pier_height: 1.5
    gem_offset_east: 0.0
    gem_offset_north: 0.0
```

These values are critical for accurate dome positioning. If your mount
provides GPS data, ARGUS will automatically synchronise the observatory
coordinates on startup.

### 4.5 Safety Settings

```yaml
safety:
  telescope_protrudes: true
  safe_altitude: 90.0
  max_nudge_while_protruding: 2.0
```

- **telescope_protrudes**: Set to `true` if the telescope optical tube extends
  into the dome slit opening. ARGUS will park the telescope before large dome
  rotations.
- **safe_altitude**: The altitude at which the telescope is safe from
  collision (e.g. 90° = zenith).
- **max_nudge_while_protruding**: Maximum dome correction in degrees that is
  allowed while the telescope is inside the slit.

### 4.6 Control Loop Settings

```yaml
control:
  update_rate: 10
  drift_correction_enabled: true
  correction_threshold: 0.5
  max_speed: 100
```

- **update_rate**: How many times per second the control loop runs (Hz).
- **drift_correction_enabled**: Set to `false` to disable vision-based drift
  correction entirely.
- **correction_threshold**: Minimum azimuth error in degrees before the dome
  motor is commanded to move (hysteresis band).
- **max_speed**: Upper limit for the proportional speed controller (0-100).

### 4.7 Settings GUI

You can also edit settings at runtime by clicking **⚙ SETTINGS** in the GUI.
Changes are written to `config.yaml` when you press **SAVE**.

## 5. Starting ARGUS

### From the command line

```bash
python src/main.py
```

### With a custom configuration file

```bash
python src/main.py --config /path/to/custom_config.yaml
```

### As an installed package

```bash
argus
argus --config /path/to/custom_config.yaml
```

## 6. User Interface

The ARGUS GUI is divided into two panels:

### 6.1 Left Panel — Video Feed

Displays the live camera feed with detected ArUco markers highlighted.
Shows "NO SIGNAL" when no camera is available.

### 6.2 Right Panel — Dashboard

The dashboard is organised into the following sections:

#### Telemetry

| Readout | Description |
|---|---|
| **MOUNT AZ** | Current telescope azimuth (from ASCOM) |
| **DOME AZ** | Current dome slit azimuth |
| **ERROR** | Difference between mount and dome azimuth |

#### Radar

A top-down view of the observatory dome. The red arrow shows the telescope
pointing direction; the yellow arc shows the dome slit position.

#### Status Indicators

| Indicator | Green | Grey |
|---|---|---|
| **ASCOM** | Telescope connected | Not connected |
| **VISION** | Camera active | No camera |
| **MOTOR** | Serial link active | Not connected |

#### Manual Control

Three buttons for direct dome movement:

- **◀ CCW** — rotate counter-clockwise
- **STOP** — emergency stop (works in all modes)
- **CW ▶** — rotate clockwise

#### Mode Selector

Switch between operating modes (see [section 7](#7-operating-modes)).

#### Settings

- **Night Mode** toggle — switches between dark-blue and red-night themes
- **⚙ SETTINGS** button — opens the settings dialog

## 7. Operating Modes

### 7.1 MANUAL

The dome only moves when you press the **CCW** or **CW** buttons. Useful for
maintenance and initial setup.

### 7.2 AUTO-SLAVE

ARGUS continuously tracks the telescope and automatically rotates the dome to
keep the slit aligned. The control loop:

1. Reads telescope RA/Dec and side-of-pier from ASCOM.
2. Calculates the required dome azimuth using vector mathematics.
3. Applies vision-based drift correction (if markers are visible).
4. Sends motor commands to the Arduino when the error exceeds the threshold.

**Degraded mode**: If the camera is lost but ASCOM and serial are still
available, ARGUS continues in "blind" mode using only mathematical predictions.

**Critical stop**: If ASCOM or the serial link is lost, motors are stopped
immediately.

### 7.3 CALIBRATE

Runs a 4-point calibration sequence (N/E/S/W at 45° altitude) to solve for
GEM mount offsets. The solved values are saved to `config.yaml` automatically.

## 8. Calibration

For the best dome tracking accuracy, run the calibration procedure after
initial installation or whenever you change the telescope setup.

1. Switch to **CALIBRATE** mode.
2. ARGUS will automatically slew the telescope and dome to four cardinal
   directions.
3. At each position, it records the dome slit azimuth.
4. A least-squares solver computes the best-fit GEM offsets and pier height.
5. The results are saved to `config.yaml`.

**Requirements**: ASCOM connection and at least a simulation sensor.

## 9. Dome Drivers & Protocols

### 9.1 Motor Types

ARGUS supports three dome motor strategies. Select the appropriate type in
`config.yaml` under `hardware.motor_type`:

| Type | Description | Key config |
|---|---|---|
| `stepper` | Open-loop stepper motor. Position derived from steps-per-degree ratio. | `steps_per_degree` |
| `encoder` | DC motor with encoder feedback (closed-loop). Stops when within tolerance. | `ticks_per_degree`, `encoder_tolerance` |
| `timed` | Relay-driven motor without sensors. Position estimated by dead reckoning. | `degrees_per_second` |

### 9.2 Communication Protocols

The `hardware.protocol` setting selects the wire format for motor commands:

| Protocol | Commands | Typical use |
|---|---|---|
| `argus` | `MOVE az speed`, `STOP`, `STATUS`, `HOME dir` | ARGUS Arduino firmware |
| `lesvedome` | `G az`, `S`, `P`, `H` | LesveDome-compatible controllers |
| `relay` | `RELAY CW`, `RELAY CCW`, `RELAY OFF` | Simple relay boards |

### 9.3 Homing

If your dome has a home-position switch, enable homing in the configuration:

```yaml
hardware:
  homing:
    enabled: true
    azimuth: 0.0       # Position of the home switch in degrees
    direction: "CW"    # Direction to search for the switch
```

ARGUS sends a HOME command on request and resets the internal position counter
to the configured azimuth.

## 10. ASCOM Alpaca Server

ARGUS includes a built-in **ASCOM Alpaca** REST server that exposes the dome
as a standard Alpaca Dome device on TCP port **11111**.

Observatory automation software such as **NINA**, **Voyager**, or **SGPro** can
connect to `http://<host>:11111/api/v1/dome/0/` and control the dome without
installing a native ASCOM driver.

### Supported Alpaca endpoints

| Endpoint | Description |
|---|---|
| `GET /azimuth` | Current dome azimuth |
| `GET /slewing` | Whether the dome is moving |
| `PUT /slewtoazimuth` | Command the dome to a target azimuth |
| `PUT /park` | Park the dome at 0° (north) |
| `PUT /abortslew` | Emergency stop |
| `PUT /findhome` | Run a homing sequence |
| `GET/PUT /slaved` | Query or set dome-slaving state |

The server starts automatically on launch and runs in a background thread.

## 11. Replay / Demo Mode

ARGUS can replay recorded telescope sessions from CSV files. This is useful for
testing, demonstrations, and verifying calibration without a live telescope.

During replay, the real ASCOM handler is temporarily swapped with a
`ReplayASCOMHandler` that feeds the recorded data into the control loop at the
original (or accelerated) playback speed.

### Supported CSV formats

1. **Semicolon-delimited** (legacy):
   `ISO_TIMESTAMP;LST;RA_MOUNT;DEC_MOUNT;HA_MOUNT;AZ_DEG;ALT_DEG;PIER_SIDE;STATUS`

2. **Comma-delimited** (with header row):
   `Timestamp_UTC_Local,Timestamp_Unix,Status,PierSide,HA_Current_Hour,Dec_Current_Deg,...`

## 12. Troubleshooting

### ASCOM Connection Failed

- Ensure the ASCOM Platform is installed.
- Verify the telescope driver ProgID in `config.yaml`.
- Check that the telescope is powered on and connected.

### Camera Not Found

- Verify the camera is connected and recognised by Windows.
- Try different `camera_index` values (0, 1, 2, …).
- ARGUS will attempt automatic camera discovery on startup.

### Serial Port Errors

- Verify the Arduino is connected to the correct COM port.
- Check Device Manager for the COM port assignment.
- Ensure no other application is using the port.
- ARGUS will attempt automatic reconnection on serial errors.

### ArUco Markers Not Detected

- Ensure markers are properly printed and mounted.
- Verify the ArUco dictionary matches the printed markers.
- Check lighting conditions (avoid glare on markers).
- Adjust camera focus.

### Voice Feedback Not Working

- Ensure `pyttsx3` is installed (`pip install pyttsx3`).
- Check that a speech engine is available on your system.

## 13. Safety Notes

- **Collision avoidance**: When `telescope_protrudes` is enabled, ARGUS will
  park the telescope before large dome rotations. Always verify that the
  parking altitude is safe for your setup.
- **Emergency stop**: The **STOP** button works in all modes and immediately
  halts dome rotation.
- **Never leave the system unattended** during the first few uses. Verify
  that the dome tracks correctly before relying on automatic operation.
- **Power failure**: Ensure your dome motor has mechanical braking or a
  fail-safe stop mechanism.

---

*ARGUS — Advanced Rotation Guidance Using Sensors*
*Copyright © 2026 Kay Schäfer. All Rights Reserved.*
