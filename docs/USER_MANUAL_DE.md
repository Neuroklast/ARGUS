# ARGUS Benutzerhandbuch

**Advanced Rotation Guidance Using Sensors**

Version 0.1.0

---

## Inhaltsverzeichnis

1. [Einführung](#1-einführung)
2. [Systemvoraussetzungen](#2-systemvoraussetzungen)
3. [Installation](#3-installation)
4. [Konfiguration](#4-konfiguration)
5. [ARGUS starten](#5-argus-starten)
6. [Benutzeroberfläche](#6-benutzeroberfläche)
7. [Betriebsmodi](#7-betriebsmodi)
8. [Kalibrierung](#8-kalibrierung)
9. [Fehlerbehebung](#9-fehlerbehebung)
10. [Sicherheitshinweise](#10-sicherheitshinweise)

---

## 1. Einführung

ARGUS ist ein hybrides Kuppelsteuerungssystem für Sternwarten. Es kombiniert
die mathematische Berechnung des erforderlichen Kuppel-Azimuts mit
Echtzeit-Bilderkennung von ArUco-Markern am Kuppelspalt.

**Hauptmerkmale:**

- ASCOM-Integration für Teleskop-Tracking-Daten (RA/Dec/SideOfPier)
- OpenCV-basierte ArUco-Markererkennung zur Driftkorrektur
- Automatische GEM-Offsetunterstützung (German Equatorial Mount)
- Arduino-Motorsteuerung über serielle Kommunikation
- Dunkles GUI-Design mit Telemetrie, Radaransicht und Sprachfeedback
- Automatische Hardwareerkennung und sanfte Degradation

## 2. Systemvoraussetzungen

### Hardware

| Komponente | Anforderung |
|---|---|
| Betriebssystem | Windows 10 oder neuer |
| Teleskopmontierung | ASCOM-kompatibel |
| Kamera | USB-Webcam |
| Motorsteuerung | Arduino mit serieller Schnittstelle |
| Kuppelspalt-Marker | Gedruckte ArUco-Marker (Standard: DICT_4X4_50) |

### Software

| Komponente | Version |
|---|---|
| Python | 3.8 oder neuer |
| ASCOM-Plattform | 6.x oder neuer |
| Arduino IDE | Zum Hochladen der Firmware (optional) |

## 3. Installation

### 3.1 Repository klonen

```bash
git clone https://github.com/Neuroklast/ARGUS.git
cd ARGUS
```

### 3.2 Python-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 3.3 Als Paket installieren (optional)

```bash
pip install -e .
```

### 3.4 Arduino-Firmware

Laden Sie den Beispiel-Sketch aus `arduino_example/dome_controller.ino` mit
der Arduino IDE auf Ihr Arduino-Board hoch. Passen Sie die Pin-Belegung an
Ihre Motorsteuerung an.

### 3.5 ArUco-Marker drucken

Drucken Sie mindestens einen ArUco-Marker aus dem DICT_4X4_50-Wörterbuch und
befestigen Sie ihn am Rand des Kuppelspalts, sodass er für die USB-Kamera
sichtbar ist.

## 4. Konfiguration

Alle Einstellungen werden in `config.yaml` im Projektverzeichnis gespeichert.

### 4.1 ASCOM-Einstellungen

```yaml
ascom:
  telescope_prog_id: "ASCOM.Simulator.Telescope"
  poll_interval: 1.0
```

- **telescope_prog_id**: Die ASCOM-ProgID Ihres Teleskoptreibers. Beim
  ersten Start öffnet ARGUS den ASCOM-Auswahldialog, wenn noch der
  Standard-Simulator konfiguriert ist.
- **poll_interval**: Abfrageintervall der Teleskop-Daten (Sekunden).

### 4.2 Kamera-Einstellungen

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

- **camera_index**: Index der USB-Kamera (0 ist normalerweise die erste).
  ARGUS sucht automatisch nach einer funktionierenden Kamera, falls der
  konfigurierte Index fehlschlägt.
- **marker_size**: Physische Größe des ArUco-Markers in Metern.

### 4.3 Hardware-Einstellungen

```yaml
hardware:
  serial_port: "COM3"
  baud_rate: 9600
  timeout: 1.0
```

- **serial_port**: Der COM-Port des Arduino.
- **baud_rate**: Muss mit der Arduino-Firmware übereinstimmen.

### 4.4 Observatoriums-Geometrie

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

Diese Werte sind entscheidend für eine präzise Kuppelpositionierung. Falls
Ihre Montierung GPS-Daten liefert, synchronisiert ARGUS die
Observatoriums-Koordinaten automatisch beim Start.

### 4.5 Sicherheitseinstellungen

```yaml
safety:
  telescope_protrudes: true
  safe_altitude: 90.0
  max_nudge_while_protruding: 2.0
```

- **telescope_protrudes**: Auf `true` setzen, wenn der Teleskoptubus in den
  Kuppelspalt hineinragt. ARGUS parkt das Teleskop vor größeren
  Kuppelrotationen.
- **safe_altitude**: Die Höhe, bei der das Teleskop kollisionsfrei ist
  (z. B. 90° = Zenit).
- **max_nudge_while_protruding**: Maximale Kuppelkorrektur in Grad, die
  erlaubt ist, während das Teleskop im Spalt steht.

### 4.6 Einstellungen über die GUI

Sie können Einstellungen auch zur Laufzeit über **⚙ SETTINGS** in der GUI
bearbeiten. Änderungen werden beim Klick auf **SAVE** in `config.yaml`
geschrieben.

## 5. ARGUS starten

### Über die Kommandozeile

```bash
python src/main.py
```

### Mit benutzerdefinierter Konfigurationsdatei

```bash
python src/main.py --config /pfad/zur/config.yaml
```

### Als installiertes Paket

```bash
argus
argus --config /pfad/zur/config.yaml
```

## 6. Benutzeroberfläche

Die ARGUS-GUI ist in zwei Bereiche unterteilt:

### 6.1 Linker Bereich — Videobild

Zeigt das Live-Kamerabild mit erkannten ArUco-Markern an.
Zeigt „NO SIGNAL", wenn keine Kamera verfügbar ist.

### 6.2 Rechter Bereich — Dashboard

Das Dashboard ist in folgende Abschnitte gegliedert:

#### Telemetrie

| Anzeige | Beschreibung |
|---|---|
| **MOUNT AZ** | Aktueller Teleskop-Azimut (von ASCOM) |
| **DOME AZ** | Aktueller Kuppelspalt-Azimut |
| **ERROR** | Differenz zwischen Montierung und Kuppel |

#### Radar

Eine Draufsicht auf die Sternwartenkuppel. Der rote Pfeil zeigt die
Teleskop-Blickrichtung; der gelbe Bogen zeigt die Kuppelspalt-Position.

#### Statusanzeigen

| Anzeige | Grün | Grau |
|---|---|---|
| **ASCOM** | Teleskop verbunden | Nicht verbunden |
| **VISION** | Kamera aktiv | Keine Kamera |
| **MOTOR** | Serielle Verbindung aktiv | Nicht verbunden |

#### Manuelle Steuerung

Drei Tasten zur direkten Kuppelbewegung:

- **◀ CCW** — gegen den Uhrzeigersinn drehen
- **STOP** — Nothalt (funktioniert in allen Modi)
- **CW ▶** — im Uhrzeigersinn drehen

#### Modus-Auswahl

Zwischen Betriebsmodi umschalten (siehe [Abschnitt 7](#7-betriebsmodi)).

#### Einstellungen

- **Night Mode** — Umschalten zwischen Dunkelblau- und Rotnacht-Design
- **⚙ SETTINGS** — Öffnet den Einstellungsdialog

## 7. Betriebsmodi

### 7.1 MANUAL

Die Kuppel bewegt sich nur durch Drücken der Tasten **CCW** oder **CW**.
Geeignet für Wartungsarbeiten und die Ersteinrichtung.

### 7.2 AUTO-SLAVE

ARGUS verfolgt das Teleskop kontinuierlich und dreht die Kuppel automatisch,
um den Spalt ausgerichtet zu halten. Die Regelschleife:

1. Liest Teleskop-RA/Dec und Side-of-Pier über ASCOM.
2. Berechnet den erforderlichen Kuppel-Azimut mittels Vektormathematik.
3. Wendet visuelle Driftkorrektur an (wenn Marker sichtbar sind).
4. Sendet Motorbefehle an den Arduino, wenn der Fehler den Schwellenwert
   überschreitet.

**Degradierter Modus**: Falls die Kamera ausfällt, aber ASCOM und Seriell
weiterhin verfügbar sind, arbeitet ARGUS im „Blind-Modus" nur mit
mathematischen Vorhersagen.

**Kritischer Stopp**: Bei Verlust von ASCOM oder der seriellen Verbindung
werden die Motoren sofort gestoppt.

### 7.3 CALIBRATE

Führt eine 4-Punkt-Kalibrierung durch (N/O/S/W bei 45° Höhe), um die
GEM-Montierungsoffsets zu bestimmen. Die errechneten Werte werden automatisch
in `config.yaml` gespeichert.

## 8. Kalibrierung

Für die bestmögliche Kuppelnachführung sollte die Kalibrierung nach der
Erstinstallation oder bei Änderungen am Teleskopaufbau durchgeführt werden.

1. Wechseln Sie in den Modus **CALIBRATE**.
2. ARGUS schwenkt Teleskop und Kuppel automatisch zu vier Himmelsrichtungen.
3. An jeder Position wird der Kuppelspalt-Azimut erfasst.
4. Ein Least-Squares-Solver berechnet die optimalen GEM-Offsets und
   Säulenhöhe.
5. Die Ergebnisse werden in `config.yaml` gespeichert.

**Voraussetzungen**: ASCOM-Verbindung und mindestens ein Simulationssensor.

## 9. Fehlerbehebung

### ASCOM-Verbindung fehlgeschlagen

- Stellen Sie sicher, dass die ASCOM-Plattform installiert ist.
- Prüfen Sie die Teleskoptreiber-ProgID in `config.yaml`.
- Überprüfen Sie, ob das Teleskop eingeschaltet und verbunden ist.

### Kamera nicht gefunden

- Überprüfen Sie, ob die Kamera angeschlossen und von Windows erkannt wird.
- Probieren Sie verschiedene `camera_index`-Werte (0, 1, 2, …).
- ARGUS versucht beim Start automatisch, eine Kamera zu finden.

### Serielle Fehler

- Prüfen Sie, ob der Arduino am richtigen COM-Port angeschlossen ist.
- Überprüfen Sie den COM-Port im Windows-Gerätemanager.
- Stellen Sie sicher, dass kein anderes Programm den Port verwendet.
- ARGUS versucht automatisch eine Neuverbindung bei seriellen Fehlern.

### ArUco-Marker werden nicht erkannt

- Stellen Sie sicher, dass die Marker korrekt gedruckt und angebracht sind.
- Prüfen Sie, ob das ArUco-Wörterbuch mit den gedruckten Markern
  übereinstimmt.
- Überprüfen Sie die Beleuchtung (Blendung auf Markern vermeiden).
- Stellen Sie den Kamerafokus ein.

### Sprachfeedback funktioniert nicht

- Stellen Sie sicher, dass `pyttsx3` installiert ist
  (`pip install pyttsx3`).
- Prüfen Sie, ob eine Sprach-Engine auf Ihrem System verfügbar ist.

## 10. Sicherheitshinweise

- **Kollisionsvermeidung**: Wenn `telescope_protrudes` aktiviert ist, parkt
  ARGUS das Teleskop vor größeren Kuppelrotationen. Überprüfen Sie stets,
  dass die Parkposition für Ihre Anlage sicher ist.
- **Nothalt**: Die Taste **STOP** funktioniert in allen Modi und stoppt die
  Kuppelrotation sofort.
- **Lassen Sie das System bei den ersten Einsätzen nie unbeaufsichtigt.**
  Stellen Sie sicher, dass die Kuppel korrekt nachgeführt wird, bevor Sie
  sich auf den Automatikbetrieb verlassen.
- **Stromausfall**: Stellen Sie sicher, dass Ihr Kuppelmotor eine
  mechanische Bremse oder einen Fail-Safe-Stopp-Mechanismus hat.

---

*ARGUS — Advanced Rotation Guidance Using Sensors*
*Copyright © 2026 Kay Schäfer. Alle Rechte vorbehalten.*
