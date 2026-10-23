# Dome tracker, part 1: R2 looks at you

*Dev log, 23 October 2026. ShadowMD Lite (PS3 Nav build) plus a Raspberry Pi 4. Tested on the droid.*

The long-term goal is a droid that moves around a room on its own, or follows you through an event. That is a long way off, so I split it into steps that each do something you can see, from the simplest up. Step one: the dome turns to look at you and keeps looking at you as you walk around it.

## The idea

A camera on the dome looks for the nearest face. If the face is to the right of the middle of the picture, the dome turns right; if it is in the middle, the dome stops. Doing it this way needs no dome position sensor and no maths about where you are in the room. The camera turns with the head, so "keep the face in the middle" is all it takes.

The brain is a Raspberry Pi 4 sitting next to the Mega ADK. It runs the face detector and talks to the Mega over USB, the same port the web console uses.

## The firmware side: one command

ShadowMD Lite already lets a PC send commands over USB (`MD:`, `S1:`, `S3:`), but none of them reach the dome motor: the SyRen hangs off `Serial2`, and only the sketch itself writes there. So I added one command:

- `DM:<speed>`, from -127 to 127, turns the dome at that speed (clamped to 80 for safety).
- **If no `DM:` arrives for 300 ms, the dome stops.** Unplug the Pi, crash the script, pull the cable: the dome stops.
- **The PS3 Nav dome stick always wins.** Move the dome by hand and the tracker is ignored for 2 seconds.
- Automatic dome mode is skipped while the tracker is driving.
- `ENABLE_DOME_TRACKER 0` and the sketch is exactly what it was.

About 40 lines, behind a `#define`. Nothing else in the sketch changed.

## First try: a webcam taped to the dome

The proof of concept was as cheap as it gets: a USB webcam taped to the front of the dome, its cable hanging loose (so no more than a turn either way), a laptop, and a Python script with OpenCV's YuNet face detector.

It detected me straight away. Then the dome started turning... away from me. I pressed `i` to invert the direction, and it still ran away. I pressed it again, and it ran away the other way.

Two things were going on, and the log I added to the script showed both:

1. **My key presses never arrived.** OpenCV only reads the keyboard while its video window has focus. The terminal had it. The log showed "inverted" off for the whole session, however many times I pressed `i`.
2. **The dome was too fast for the camera.** In less than half a second my face crossed the whole picture, from one edge to the other. By the time the script saw me in the middle, the dome had already gone past, lost me, and turned back. From in front of the droid, that looks exactly like a dome avoiding you.

With the speed lowered and the window clicked, the direction turned out to be inverted for my mounting, and from then on it followed me. Slowly, though.

## Making it follow at a natural speed

Slow is safe but it does not look alive. Turning faster made it overshoot again. The fix was to look at where the face is *heading*, not just where it is:

- **Face moving away from the middle:** turn faster, to catch up.
- **Face coming back to the middle**, because the dome is catching up: brake before getting there.

That is a classic proportional plus derivative controller. With it, the top speed went from 28 to 58 with no overshoot. The values I ended up with on my droid: minimum 18, maximum 58, `kd` 0.3, and a centre band of 15% where the dome does not move.

## When it loses you

If nobody is in front of the camera for 1.5 seconds, the dome goes back to the front. Without an angle sensor, how does it know where the front is? The camera tells it: while the dome turns, the whole room slides across the picture, and measuring that slide frame by frame (phase correlation, built into OpenCV) adds up how far the dome has turned. It is not as precise as a sensor, and it drifts over a long session, but it costs nothing. It is in the code, but it needs more testing on the droid.

## Moving to the Raspberry Pi

I had a Pi 4 (4 GB) in a box, last used for Home Assistant. Fresh Raspberry Pi OS, the same script, the webcam and the Mega moved from the laptop to the Pi's USB ports.

First measurement: 10 frames per second, against 25 on the laptop. The camera was not the problem (25 fps on the Pi too). The detector was: 90 ms per picture at 640x480. Running it on a 320x240 copy of the picture brought that down to 21 ms, and the Pi tracks at 25 fps, the same as the laptop. At that size the detector loses range (a face far away is only a few pixels), but across a room it is fine.

Then the things that matter when nobody is sitting at a keyboard:

- **It starts by itself** when the Pi boots (a systemd service), and restarts if it stops.
- **It waits for the Mega.** Plug the Mega in late and the tracker picks it up within 5 seconds, without restarting anything.
- **It should not reset the Mega when it restarts.** Opening the Mega's USB port resets it, which you do not want while driving. The service keeps the port's DTR line up between runs, so only the first open after the Pi boots should reset it. That one I still have to check on the droid with the tracker restarting.
- **You can see what it sees.** The Pi serves a web page with the Astromech Spain logo and the live picture, with the face box and the speed it is sending. It opens full screen on the Pi's HDMI monitor at boot, and any phone on the same WiFi can open it too.

## Where it stands

On the droid: the dome follows me left and right at a natural speed, with the PS3 Nav still in charge. It runs from the Pi alone, starts at power on, and shows its picture on a monitor or a phone.

The obvious limit is the cable: a USB webcam on the dome means the dome cannot keep turning the same way. It also only knows faces, so it loses you when you turn your back.

## Next: a camera that turns with the dome

The cable has to go. I looked at three ways:

- **The same USB webcam through the slip ring.** I have three spare wires, but they run unshielded next to the 12 V line, and USB 2.0 wants 480 Mbit/s on a proper twisted pair. Very unlikely to be reliable, and a short to 12 V would kill a USB port on the Pi.
- **An ESP32-S3 camera streaming over WiFi.** Cheap and tiny, but too weak to detect faces at any distance itself, and streaming the video to the Pi adds 100 to 200 ms of lag. Lag is exactly what made the dome overshoot at the start.
- **A Raspberry Pi Zero 2 W with a Camera Module 3 Wide (120°) in the dome.** It runs the same detector itself and sends only "face at +12°" to the Pi 4, a few bytes every 40 ms, over those three spare slip ring wires as a slow serial link (RS-485 to shrug off the noise from the 12 V wires). No WiFi, almost no lag. This is the one.

The Pi 4 stays in the body as the brain: it takes the bearing from the dome, drives the Mega, and shows the picture. About 100 € to buy for one camera at the front; a second Zero at the back later would let the dome turn round when you walk behind it. The full list is below.

After that:

- **A dome angle sensor** (an AS5600 on the slip ring axis), for a real "front".
- **Following with the whole droid**, and later moving around a room on its own with a lidar and ROS 2.

## Bill of materials

**What the proof of concept used** (all of it was already on the bench):

| Part | ~€ |
|---|---|
| Raspberry Pi 4 Model B, 4 GB, with a 32 GB microSD | 70 |
| Any USB webcam (UVC), taped to the dome | 15 |
| USB cable Pi 4 to Mega ADK | 3 |
| Mega ADK, USB Host Shield, SyRen, dome motor | already in the droid |

**The next version** (camera turning with the dome, one at the front):

| Part | ~€ |
|---|---|
| Raspberry Pi Zero 2 W (WH) + microSD | 26 |
| Raspberry Pi Camera Module 3 Wide (120°) + Pi Zero camera cable | 43 |
| Buck 12 V to 5 V 3 A in the dome, with an inline 1 A fuse | 12–18 |
| 2 RS-485 modules, 3.3 V (MAX3485), one each end | 4 |
| Buck from the droid battery to 5 V for the Pi 4, with fuse | 12–20 |

Rough October 2026 prices. Optional later: a second Zero and camera for the back (~70 €), and an AS5600 with a magnet for the dome angle (~5 €).

The code: the `DM:` command is on the `droid` branch of ShadowMD Lite, and the tracker is a new project, DomeTracker. Neither is public yet; links when they are.
