# Arduino Dome Controller Example

This directory contains an example Arduino sketch for controlling a motorized dome.

## Overview

The `dome_controller.ino` sketch implements the serial communication protocol expected by ARGUS's SerialController class.

## Hardware Requirements

- Arduino board (Uno, Mega, etc.)
- Motor controller (H-bridge or motor driver)
- Stepper or DC motor for dome rotation
- Optional: Rotary encoder for position feedback

## Pin Configuration

Default pins (modify as needed for your hardware):
- Pin 9: Motor PWM (speed control)
- Pin 8: Motor direction
- Pin 2: Encoder A (optional)
- Pin 3: Encoder B (optional)

## Serial Protocol

Baud rate: 9600

### Commands

1. **MOVE** - Move dome to target azimuth
   ```
   MOVE <azimuth> <speed>
   ```
   - `azimuth`: Target position in degrees (0-360)
   - `speed`: Motor speed (0-100)
   - Example: `MOVE 180.50 50`

2. **STOP** - Emergency stop
   ```
   STOP
   ```

3. **STATUS** - Query current status
   ```
   STATUS
   ```
   - Returns: `STATUS: Azimuth=<current> Target=<target> Moving=<YES/NO>`

## Installation

1. Open `dome_controller.ino` in Arduino IDE
2. Adjust pin assignments for your hardware
3. Upload to your Arduino board
4. Test with Serial Monitor before connecting to ARGUS

## Customization

This is a basic example. You should adapt it to:
- Your specific motor controller
- Add encoder-based position tracking
- Implement limit switches
- Add safety features
- Calibrate speed and acceleration profiles

## Testing

Use Arduino Serial Monitor to test commands:
```
MOVE 90 30
STATUS
STOP
```
