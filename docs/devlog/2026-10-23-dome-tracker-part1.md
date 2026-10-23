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

## Next

- **A wireless camera on the dome:** an ESP32-S3 with a 120° OV2640 or OV3660 camera, powered from the 12 V that already goes up the slip ring, streaming over WiFi to the Pi. The Pi keeps doing the detection, and the script barely changes.
- **A dome angle sensor** (an AS5600 on the slip ring axis), for a real "front".
- **Following with the whole droid**, and later moving around a room on its own with a lidar and ROS 2.

The code: the `DM:` command is on the `droid` branch of ShadowMD Lite, and the tracker is a new project, DomeTracker. Neither is public yet; links when they are.
