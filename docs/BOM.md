# DomeTracker: bill of materials

Prices are rough, in euros, October 2026. Check them when you buy.

## What the proof of concept used

Everything here was already on the bench; nothing was bought.

| Part | Used for | ~€ |
|---|---|---|
| Raspberry Pi 4 Model B, 4 GB | The brain, next to the Mega: face detection, speed control, web view | 60 |
| microSD 32 GB | Raspberry Pi OS (64 bit) | 8 |
| USB webcam (any UVC webcam; ours is a "GENERAL WEBCAM", 640x480) | The eye, taped to the front of the dome | 15 |
| USB A to USB B cable | Pi 4 to the Mega ADK | 3 |
| Official Pi 4 power supply (5 V 3 A, USB-C) | Power on the bench | 10 |
| Micro HDMI to HDMI cable, monitor | Optional: watching what the camera sees | 6 |
| Mega ADK, USB Host Shield, SyRen, dome motor | Already in the droid (ShadowMD Lite) | — |

Limit: the webcam's USB cable hangs from the dome, so the dome cannot keep turning the same way.

## The next version: a camera that turns with the dome

The dome turns without end on its slip ring, so the camera cannot reach the Pi 4 by USB. A USB 2.0 webcam over unshielded slip ring wires next to the 12 V line is very unlikely to be reliable (it needs 480 Mbit/s on a matched twisted pair). Instead, a small Raspberry Pi in the dome does the detection itself and sends only "face at +12°" to the Pi 4, a few bytes every 40 ms, over three spare slip ring wires.

### In the dome

| Part | Qty | Used for | ~€ |
|---|---|---|---|
| Raspberry Pi Zero 2 W (WH, with header) | 1 | Detects the face, sends the bearing | 20 |
| Raspberry Pi Camera Module 3 **Wide** (120°, autofocus) | 1 | The eye, behind the radar eye or the front panel | 40 |
| Pi Zero camera cable (22 to 15 pin; the Pi 4 cable does not fit the Zero) | 1 | Camera to Zero | 3 |
| microSD 16–32 GB | 1 | Raspberry Pi OS Lite | 6 |
| DC-DC buck 12 V → 5 V, 3 A (e.g. Pololu D24V22F5 or a good MP1584/LM2596 module) | 1 | Power from the 12 V that already goes up the slip ring | 8–15 |
| Inline fuse holder + 1 A fuse | 1 | A fault here does not take the dome down | 3 |
| RS-485 module, 3.3 V (MAX3485) | 1 | Recommended: differential link, shrugs off the noise from the 12 V wires | 2 |
| 3D printed mount | 1 | Camera behind the radar eye, Zero inside the dome | — |

### Across the slip ring

| Wires | With RS-485 (recommended) | Plain serial (3.3 V TTL) |
|---|---|---|
| 1 | A | Zero TX → Pi 4 RX |
| 2 | B | Pi 4 TX → Zero RX (optional) |
| 3 | GND (signal ground) | GND (signal ground) |

115200 baud or less. Both Pis are 3.3 V, so plain serial needs no level shifting; RS-485 is there for noise.

### In the body

| Part | Qty | Used for | ~€ |
|---|---|---|---|
| Raspberry Pi 4 (the one above) | 1 | Receives the bearing, drives the Mega, web view | — |
| RS-485 module, 3.3 V (MAX3485) | 1 | Other end of the link (if using RS-485) | 2 |
| DC-DC buck from the droid battery → 5 V, 3 A or more, with fuse | 1 | Powers the Pi 4 in the droid, never from the Mega | 12–20 |
| Short USB A to B cable | 1 | Pi 4 to the Mega | 3 |

**Total to buy for the next version: about 95–110 €** (one camera, front).

### Later, optional

| Part | Used for | ~€ |
|---|---|---|
| A second Pi Zero 2 W + Camera Module 3 Wide (+ cable, microSD) | A camera at the back: the dome turns round when you walk behind it | 70 |
| AS5600 magnetic encoder + diametric magnet | The dome's real angle, on the slip ring axis, for an exact "front" | 5 |
