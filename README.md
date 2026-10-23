# DomeTracker

R2-D2's dome turns to look at you. A camera on the dome finds the nearest face, and a Raspberry Pi (or a PC) tells the droid's Mega ADK how fast to turn the dome so the face stays in the middle of the picture.

This is a proof of concept, and it works on the droid. It is the first step of a longer plan: the dome looks at you, then the droid follows you, then it moves around a room on its own.

## How it works

```
 webcam on the dome ──USB──> Raspberry Pi 4 ──USB──> Mega ADK (ShadowMD Lite) ──> SyRen ──> dome motor
                              face detector           DM:<speed>
                              speed control
```

- **Raspberry Pi 4** (or a PC) runs `poc/dome_tracker_poc.py`: OpenCV's YuNet face detector, then a speed controller.
- **Mega ADK** runs [ShadowMD Lite](https://github.com/Fernando-Beltran/ShadowMDLite) with `ENABLE_DOME_TRACKER 1` (branch `droid`). It accepts `DM:<speed>` on the USB serial port and turns the dome at that speed.

### Safety, in the firmware
- The dome stops if no `DM:` arrives for 300 ms (Pi off, script crashed, cable out).
- The PS3 Nav dome stick always wins. After you move the dome by hand, `DM:` is ignored for 2 s.
- `ENABLE_DOME_TRACKER 0` builds the sketch exactly as before.

### Speed control
- The further the face is from the centre, the faster the dome turns, between `--min` and `--max`.
- The face's own movement counts too (`--kd`): moving away speeds the dome up, coming back to the centre brakes it before it overshoots.
- A centre band (`--deadzone`) where the dome stays still.
- Lose the face for 1.5 s and the dome goes back to the front. With no angle sensor yet, "front" is measured from how far the room slid across the picture while the dome turned.

Values tuned on the droid: `--min 18 --max 58 --kd 0.3 --deadzone 0.15`, direction inverted (the default).

## Running it on a PC

```
pip install opencv-python pyserial
python poc/dome_tracker_poc.py --list-cameras
python poc/dome_tracker_poc.py --camera 1 --port COM5
```

Without `--port` nothing is sent, so you can see what the detector does first. Keys work only when the video window has focus (click it first): space pause, `i` invert, `+`/`-` max speed, `[`/`]` min speed, `,`/`.` kd, `h` front is here, `r` go to front, `q` quit.

## Running it on a Raspberry Pi 4

Tested on a Pi 4 Model B 4 GB, Raspberry Pi OS (Debian 13), with the GENERAL WEBCAM and the Mega on USB. It runs at 25 frames per second, with the detector working on a 320 px wide copy of the picture.

```
python3 -m venv ~/dome-venv
~/dome-venv/bin/pip install opencv-python-headless pyserial
# copy poc/ to ~/dome
sudo cp ~/dome/dome-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dome-tracker
```

`dome-tracker.service` starts the tracker at boot and restarts it if it stops. It uses stable device names (`/dev/v4l/by-id/...`, `/dev/serial/by-id/...`; edit them for your camera and Mega). If the Mega is not plugged in, it carries on and connects when the Mega appears. It keeps the serial line's DTR up, so a restart does not reset the Mega.

The picture, with the Astromech Spain logo, is served at `http://<pi>:8080`. With the Pi desktop, `r2-dome-view.desktop` in `~/.config/autostart/` opens it full screen on the HDMI monitor (Alt+F4 closes it). Without a desktop, `--fb /dev/fb0` draws it straight onto the monitor.

```
journalctl -u dome-tracker -f        # what it is doing
sudo systemctl stop dome-tracker     # stop it
```

## What is next

- **Wireless camera on the dome:** an ESP32-S3 with an OV2640/OV3660 120° camera streaming over WiFi to the Pi, instead of a USB cable that limits how far the dome can turn.
- **Dome angle sensor** (AS5600 on the slip ring axis), for a real "front".
- **The droid follows you**, then **moves around a room** (lidar, ROS 2).

## Credits

- Face detector: [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) from the OpenCV Zoo (MIT licence), `poc/models/`.
- Logo: [Astromech Spain](https://www.astromechspain.com/), `poc/assets/`. It belongs to the club.
