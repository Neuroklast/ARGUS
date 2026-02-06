/*
 * ARGUS Dome Motor Controller
 * Arduino firmware for controlling dome rotation motors
 * 
 * This is an example sketch showing the expected command protocol.
 * Adapt this code to your specific motor controller hardware.
 * 
 * Commands:
 *   MOVE <azimuth> <speed>  - Move to azimuth (0-360) at speed (0-100)
 *   STOP                    - Emergency stop
 *   STATUS                  - Return current position and status
 */

// Motor control pins (adjust for your hardware)
const int MOTOR_PWM_PIN = 9;
const int MOTOR_DIR_PIN = 8;
const int ENCODER_PIN_A = 2;
const int ENCODER_PIN_B = 3;

// State variables
float currentAzimuth = 0.0;
float targetAzimuth = 0.0;
int motorSpeed = 0;
bool moving = false;

void setup() {
  Serial.begin(9600);
  
  // Configure motor pins
  pinMode(MOTOR_PWM_PIN, OUTPUT);
  pinMode(MOTOR_DIR_PIN, OUTPUT);
  pinMode(ENCODER_PIN_A, INPUT_PULLUP);
  pinMode(ENCODER_PIN_B, INPUT_PULLUP);
  
  Serial.println("ARGUS Dome Controller Ready");
}

void loop() {
  // Check for incoming commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processCommand(command);
  }
  
  // Update motor control
  updateMotorControl();
  
  delay(10);
}

void processCommand(String cmd) {
  if (cmd.startsWith("MOVE")) {
    // Parse MOVE command: MOVE <azimuth> <speed>
    int firstSpace = cmd.indexOf(' ');
    int secondSpace = cmd.indexOf(' ', firstSpace + 1);
    
    if (firstSpace > 0 && secondSpace > 0) {
      float azimuth = cmd.substring(firstSpace + 1, secondSpace).toFloat();
      int speed = cmd.substring(secondSpace + 1).toInt();
      
      targetAzimuth = constrainAngle(azimuth);
      motorSpeed = constrain(speed, 0, 100);
      moving = true;
      
      Serial.print("MOVE: Target=");
      Serial.print(targetAzimuth);
      Serial.print(" Speed=");
      Serial.println(motorSpeed);
    }
  }
  else if (cmd.startsWith("STOP")) {
    stopMotor();
    Serial.println("STOPPED");
  }
  else if (cmd.startsWith("STATUS")) {
    Serial.print("STATUS: Azimuth=");
    Serial.print(currentAzimuth);
    Serial.print(" Target=");
    Serial.print(targetAzimuth);
    Serial.print(" Moving=");
    Serial.println(moving ? "YES" : "NO");
  }
  else {
    Serial.println("ERROR: Unknown command");
  }
}

void updateMotorControl() {
  if (!moving) {
    return;
  }
  
  // Calculate error
  float error = calculateShortestRotation(currentAzimuth, targetAzimuth);
  float absError = abs(error);
  
  // Check if we've reached target
  if (absError < 0.5) {
    stopMotor();
    moving = false;
    Serial.println("TARGET REACHED");
    return;
  }
  
  // Determine direction
  bool clockwise = error > 0;
  digitalWrite(MOTOR_DIR_PIN, clockwise ? HIGH : LOW);
  
  // Set speed (proportional control with minimum speed)
  int pwm = map(min(absError, 90.0), 0, 90, 50, 255);
  pwm = constrain(pwm * motorSpeed / 100, 0, 255);
  analogWrite(MOTOR_PWM_PIN, pwm);
  
  // Update current position (simplified - use encoder in real implementation)
  float deltaAz = (clockwise ? 0.1 : -0.1);
  currentAzimuth = constrainAngle(currentAzimuth + deltaAz);
}

void stopMotor() {
  analogWrite(MOTOR_PWM_PIN, 0);
  moving = false;
}

float constrainAngle(float angle) {
  while (angle < 0) angle += 360.0;
  while (angle >= 360) angle -= 360.0;
  return angle;
}

float calculateShortestRotation(float from, float to) {
  float diff = to - from;
  
  // Normalize to -180 to 180
  while (diff > 180) diff -= 360;
  while (diff < -180) diff += 360;
  
  return diff;
}
