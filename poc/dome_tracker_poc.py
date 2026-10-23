"""Dome tracker PoC: the webcam (taped to the dome) looks for a face and the PC turns the dome
so the face stays in the middle of the picture, sending DM:<speed> to the Mega over USB.

Throwaway proof of concept. Needs ShadowMDLite with ENABLE_DOME_TRACKER 1.

    python dome_tracker_poc.py --list-cameras
    python dome_tracker_poc.py --camera 1 --port COM5
    python dome_tracker_poc.py --camera 1            (no Mega: only shows what it would send)

Keys in the video window:
    space  pause / resume (pause stops the dome)
    i      invert direction (if the dome turns away from you)
    + / -  max speed up / down
    [ / ]  min speed down / up (the speed that just gets the dome moving)
    , / .  kd down / up (0 = only where the face is; more = follows the face's speed, brakes sooner)
    h      the dome is looking to the front now (it goes back here 1.5 s after losing you)
    r      go back to the front now
    q, Esc quit (stops the dome)
"""

import argparse
import os
import sys
import time

import cv2

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models",
                     "face_detection_yunet_2023mar.onnx")
SEND_PERIOD_S = 0.066   # ~15 DM: per second; the Mega stops the dome after 300 ms without one
# DirectShow opens USB webcams fastest on Windows; V4L2 is the Linux (Raspberry Pi) driver.
CAM_BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_V4L2
LOST_AFTER_S = 0.2      # no face for this long -> dome stops
RETURN_AFTER_S = 1.5    # no face for this long -> dome goes back to the front
HOME_BAND = 0.08        # close enough to the front (in half-picture widths)


def list_cameras():
    for i in range(6):
        cap = cv2.VideoCapture(i, CAM_BACKEND)
        if cap.isOpened():
            ok, frame = cap.read()
            size = f"{frame.shape[1]}x{frame.shape[0]}" if ok else "no image"
            print(f"camera {i}: {size}")
        cap.release()


class Mega:
    """DM: sender. With no port it only prints, so the effect can be tried without the droid.
    If the port is missing (Mega unplugged or off) it keeps going and tries again every 5 s."""

    def __init__(self, port):
        self.port = port
        self.ser = None
        self.next_try = 0.0
        self.last = None
        self.rx = ""
        self.log = None
        self.connect()

    def connect(self):
        if not self.port or self.ser or time.time() < self.next_try:
            return
        import serial
        try:
            self.ser = serial.Serial(self.port, 115200, timeout=0)
        except (serial.SerialException, OSError):
            if self.next_try == 0.0:
                print(f"No Mega on {self.port}; trying again every 5 s", flush=True)
            self.next_try = time.time() + 5
            return
        print(f"Opened {self.port}; the Mega may reset on open, waiting 3 s...", flush=True)
        time.sleep(3)
        self.ser.reset_input_buffer()

    def send(self, speed):
        line = f"DM:{speed}\n"
        self.connect()
        if self.ser:
            try:
                self.ser.write(line.encode("ascii"))
                # Keep what the Mega says about the dome (its debug output) in the log.
                self.rx += self.ser.read(self.ser.in_waiting or 1).decode("ascii", "replace")
            except OSError:
                print("Lost the Mega; trying again every 5 s", flush=True)
                self.ser = None
                self.next_try = time.time() + 5
                return
            *lines, self.rx = self.rx.replace("\r", "\n").split("\n")
            for raw in lines:
                if raw.startswith("ERR"):
                    print("Mega:", raw)
                if self.log and ("Dome" in raw or "ERR" in raw):
                    self.log.write(f"{time.time():.3f},MEGA,{raw.strip()}\n")
        elif not self.port and speed != self.last:
            print(line.strip())
        self.last = speed

    def close(self):
        if self.ser:
            try:
                for _ in range(3):
                    self.ser.write(b"DM:0\n")
                    time.sleep(0.05)
                self.ser.close()
            except OSError:
                pass


class FbDisplay:
    """Shows the picture full screen on the HDMI monitor with no desktop, by writing straight
    into the Linux framebuffer. Only while the first console (Ctrl+Alt+F1) is on screen, so
    Ctrl+Alt+F2 gives a normal text console to type in."""

    BG_COLOUR = (40, 20, 12)        # BGR, dark navy
    LOGO_H = 120                    # logo height on screen, px

    def __init__(self, dev, logo_path=None):
        import numpy as np
        sysfs = "/sys/class/graphics/" + os.path.basename(dev)
        self.w, self.h = map(int, open(sysfs + "/virtual_size").read().split(","))
        self.bytes_pp = int(open(sysfs + "/bits_per_pixel").read()) // 8
        stride = int(open(sysfs + "/stride").read())
        self.fb = np.memmap(dev, dtype=np.uint8, mode="r+", shape=(self.h, stride))
        self.was_shown = False

        # Background: dark, with the Astromech Spain logo centred at the top. The camera picture
        # goes in the area below it.
        bg = np.zeros((self.h, self.w, 3), np.uint8)
        bg[:] = self.BG_COLOUR
        top = 0
        logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED) if logo_path else None
        if logo is not None and logo.shape[2] == 4:
            lw = int(logo.shape[1] * self.LOGO_H / logo.shape[0])
            logo = cv2.resize(logo, (lw, self.LOGO_H), interpolation=cv2.INTER_CUBIC)
            alpha = logo[:, :, 3:4].astype(np.float32) / 255
            x, y = (self.w - lw) // 2, 30
            area = bg[y:y + self.LOGO_H, x:x + lw]
            area[:] = (logo[:, :, :3] * alpha + area * (1 - alpha)).astype(np.uint8)
            top = y + self.LOGO_H + 30
        self.bg = self.to_fb(bg)
        self.area = (top, self.h - top - 20)     # y and height left for the camera picture

    def to_fb(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGR565 if self.bytes_pp == 2 else cv2.COLOR_BGR2BGRA)
        return img.reshape(img.shape[0], -1)

    @staticmethod
    def on_screen():
        try:
            return open("/sys/class/tty/tty0/active").read().strip() == "tty1"
        except OSError:
            return True

    def show(self, frame):
        if not self.on_screen():
            self.was_shown = False
            return
        if not self.was_shown:
            self.fb[:, :self.bg.shape[1]] = self.bg     # logo background, over the console text
            self.was_shown = True
        top, area_h = self.area
        fh, fw = frame.shape[:2]
        scale = min(self.w / fw, area_h / fh)
        tw, th = int(fw * scale), int(fh * scale)
        img = self.to_fb(cv2.resize(frame, (tw, th), interpolation=cv2.INTER_NEAREST))
        x0, y0 = (self.w - tw) // 2, top
        self.fb[y0:y0 + th, x0 * self.bytes_pp:(x0 + tw) * self.bytes_pp] = img


WEB_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>R2 dome tracker</title>
<style>
  html, body { margin: 0; height: 100%; background: #0c1428; }
  body { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3vh; }
  img.logo { height: 10vh; max-width: 90vw; object-fit: contain; }
  img.cam { max-height: 76vh; max-width: 96vw; border-radius: 8px; box-shadow: 0 0 40px #0008; }
  a.web { color: #c8d2e6; font: 2.2vh sans-serif; text-decoration: none; letter-spacing: .05em; }
  a.web:hover { color: #fff; }
  #close { display: none; position: fixed; top: 2vh; right: 2vh; padding: 1.2vh 2.4vh;
           font: bold 2.2vh sans-serif; color: #fff; background: #c0392b; border: 0;
           border-radius: 6px; cursor: pointer; }
</style></head>
<body>
  <a href="https://www.astromechspain.com/" target="_blank"><img class="logo" src="/logo.png" alt="Astromech Spain"></a>
  <img class="cam" src="/stream" alt="camera">
  <a class="web" href="https://www.astromechspain.com/" target="_blank">www.astromechspain.com</a>
  <button id="close" title="Cierra esta pantalla; el dome tracker sigue funcionando">Cerrar</button>
  <script>
    // "Cerrar" only on the Pi's own monitor: it closes this full-screen window there.
    const close = document.getElementById("close");
    if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
      close.style.display = "block";
      close.onclick = () => fetch("/close", {method: "POST"});
    }
    // If the tracker restarts, the video stops: reload the page once it answers again.
    let down = false;
    setInterval(() => fetch("/", {cache: "no-store"})
      .then(() => { if (down) location.reload(); })
      .catch(() => { down = true; }), 2000);
  </script>
</body></html>
"""


class WebView:
    """The picture as a web page, http://<pi>:<port>: Astromech Spain logo on top, live camera
    below. Opened full screen on the Pi's monitor, and from a phone or PC on the same WiFi."""

    def __init__(self, port, logo_path):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        self.jpeg = None
        self.cond = threading.Condition()
        logo = open(logo_path, "rb").read() if os.path.exists(logo_path) else b""
        view = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, ctype, body):
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/":
                    self.reply("text/html; charset=utf-8", WEB_PAGE.encode())
                elif self.path == "/logo.png":
                    self.reply("image/png", logo)
                elif self.path == "/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    try:
                        while True:
                            with view.cond:
                                view.cond.wait(timeout=2)
                                jpg = view.jpeg
                            if jpg:
                                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                                 + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                else:
                    self.send_error(404)

            def do_POST(self):
                # The page's "Cerrar" button: closes the full-screen view on the Pi's monitor.
                # Only from the Pi itself, so a phone watching the page cannot close it.
                if self.path == "/close" and self.client_address[0] in ("127.0.0.1", "::1"):
                    self.reply("text/plain", b"ok")
                    import subprocess
                    subprocess.run(["pkill", "-f", "chromium.*localhost:" + str(port)])
                else:
                    self.send_error(403)

        server = ThreadingHTTPServer(("", port), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"Web view on port {port}", flush=True)

    def show(self, frame):
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            with self.cond:
                self.jpeg = buf.tobytes()
                self.cond.notify_all()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camera", default="1", help="camera index (see --list-cameras) or a video URL")
    ap.add_argument("--port", help="Mega COM port, e.g. COM5; without it nothing is sent")
    ap.add_argument("--max", type=int, default=58, help="dome speed with the face at the edge")
    ap.add_argument("--min", type=int, default=18, help="dome speed just outside the dead zone")
    ap.add_argument("--kd", type=float, default=0.3,
                    help="how much the face's own speed counts, in seconds: higher = catches up and brakes sooner")
    ap.add_argument("--deadzone", type=float, default=0.15, help="centre band with no movement, 0-1")
    ap.add_argument("--invert", action=argparse.BooleanOptionalAction, default=True,
                    help="turn the other way (default on: right for this droid; --no-invert to undo)")
    ap.add_argument("--detect-width", type=int, default=320,
                    help="picture width the face detector works at (smaller = faster, shorter range)")
    ap.add_argument("--log", action=argparse.BooleanOptionalAction, default=True,
                    help="write a CSV line per frame to logs/ (--no-log when running as a service)")
    ap.add_argument("--fb", help="also show the picture on this framebuffer, e.g. /dev/fb0 (HDMI monitor, no desktop)")
    ap.add_argument("--http", type=int, help="also serve the picture as a web page on this port, e.g. 8080")
    ap.add_argument("--headless", action="store_true",
                    help="no video window (Raspberry Pi over SSH): prints fps and status, Ctrl+C quits")
    ap.add_argument("--list-cameras", action="store_true")
    args = ap.parse_args()

    if args.list_cameras:
        list_cameras()
        return

    if args.camera.isdigit():
        cap = cv2.VideoCapture(int(args.camera), CAM_BACKEND)
    else:
        # A /dev path (e.g. /dev/v4l/by-id/..., stable across reboots) or a video URL.
        cap = cv2.VideoCapture(args.camera, CAM_BACKEND) if args.camera.startswith("/dev/")             else cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)     # always the newest frame: lag makes the dome overshoot
    if not cap.isOpened():
        sys.exit(f"Cannot open camera {args.camera}; try --list-cameras")

    detector = None
    mega = Mega(args.port)
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "astromech_spain_logo_w.png")
    screens = []
    if args.fb:
        try:
            screens.append(FbDisplay(args.fb, logo_path))
        except OSError as e:
            print(f"No monitor on {args.fb}: {e}", flush=True)
    if args.http:
        screens.append(WebView(args.http, logo_path))
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs",
                            time.strftime("track-%Y%m%d-%H%M%S.csv"))
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    if not args.log:
        log_path = os.devnull       # running as a service: a frame log would fill the SD card
    log = open(log_path, "w", buffering=1)
    log.write("t,kind,face_err,smooth_err,speed,invert,face_w,rate,kd,pan,returning\n")
    mega.log = log
    print("Log:", log_path)
    paused = False
    smooth_err = 0.0
    rate = 0.0              # how fast the face moves across the picture, image-halves per second
    prev_err, prev_t = None, 0.0
    last_face_t = 0.0
    last_send_t = 0.0
    speed = 0

    # Where the dome points, measured by how far the room slides across the picture (no angle
    # sensor yet). Same unit as the face error: 1.0 = half the picture width. 0 = front.
    pan = 0.0
    prev_small = None
    last_moving_t = 0.0     # last time the dome was told to move (it coasts a little after)
    returning = False       # going back to the front after losing the face
    fps_t, frames = time.time(), 0

    def speed_for(u, top):
        """DM: speed that moves the picture centre towards u (same sign as a face error)."""
        mag = args.min + (top - args.min) * min(abs(u), 1.0)
        return int(round(mag)) * (1 if u > 0 else -1) * (-1 if args.invert else 1)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("No image from the camera")
                break
            h, w = frame.shape[:2]
            if detector is None:
                det_w = min(args.detect_width, w)
                det_h = int(round(h * det_w / w))
                detector = cv2.FaceDetectorYN.create(MODEL, "", (det_w, det_h), 0.6)

            # Detect on a smaller copy (4x faster on a Raspberry Pi 4), boxes scaled back up.
            _, faces = detector.detect(cv2.resize(frame, (det_w, det_h)) if det_w != w else frame)
            if faces is not None:
                faces[:, :4] *= w / det_w
            now = time.time()

            # Dome rotation from the room sliding across the picture. Only counted while the
            # dome moves (and briefly after), so a person walking past does not shift "front".
            small = cv2.cvtColor(cv2.resize(frame, (160, 120)), cv2.COLOR_BGR2GRAY).astype("float32")
            if prev_small is not None and now - last_moving_t < 0.5:
                (dx, _), resp = cv2.phaseCorrelate(prev_small, small)
                if resp > 0.05 and abs(dx) > 0.15:
                    pan -= dx / 80.0        # room slides left = camera turned right = pan grows
            prev_small = small

            target = None
            if faces is not None and len(faces):
                # Look at the biggest face: the closest person.
                target = max(faces, key=lambda f: f[2] * f[3])
                x, y, fw, fh = target[:4].astype(int)
                cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)
                err = ((x + fw / 2) - w / 2) / (w / 2)          # -1 left edge .. +1 right edge
                smooth_err = 0.5 * smooth_err + 0.5 * err       # calm the jitter between frames
                if prev_err is not None and 0 < now - prev_t < 0.2:
                    rate = 0.6 * rate + 0.4 * (err - prev_err) / (now - prev_t)
                prev_err, prev_t = err, now
                last_face_t = now

            if target is not None:
                returning = False
            elif not paused and now - last_face_t > RETURN_AFTER_S and abs(pan) > HOME_BAND:
                returning = True

            if paused:
                speed = 0
                returning = False
            elif returning:
                # Back to the front, slower as it gets close; picks the face up again on the way.
                if abs(pan) <= HOME_BAND:
                    returning = False
                    speed = 0
                else:
                    speed = speed_for(-pan / 0.5, (args.min + args.max) // 2)
            elif now - last_face_t > LOST_AFTER_S:
                speed = 0
            else:
                # Where the face is plus where it is heading: moving out speeds the dome up,
                # coming back to the centre (the dome catching up) brakes it before it overshoots.
                u = smooth_err + args.kd * rate
                if abs(u) < args.deadzone or (u > 0) != (smooth_err > 0):
                    speed = 0
                else:
                    frac = (abs(u) - args.deadzone) / (1 - args.deadzone)
                    speed = speed_for(frac if u > 0 else -frac, args.max)

            if target is None:
                smooth_err = 0.0
                rate = 0.0
                prev_err = None
            if speed != 0:
                last_moving_t = now

            if target is not None:
                log.write(f"{now:.3f},FRAME,{err:.3f},{smooth_err:.3f},{speed},{int(args.invert)},{fw},{rate:.3f},{args.kd:.2f},{pan:.3f},{int(returning)}\n")
            else:
                log.write(f"{now:.3f},FRAME,,{smooth_err:.3f},{speed},{int(args.invert)},,{rate:.3f},{args.kd:.2f},{pan:.3f},{int(returning)}\n")

            if now - last_send_t >= SEND_PERIOD_S:
                mega.send(speed)
                last_send_t = now

            # Overlay
            dz = int(args.deadzone * w / 2)
            cv2.rectangle(frame, (w // 2 - dz, 0), (w // 2 + dz, h), (255, 200, 0), 1)
            status = ("PAUSED" if paused else "returning" if returning
                      else "no face" if target is None else "tracking")
            cv2.putText(frame, f"{status}  DM:{speed}  min {args.min} max {args.max} kd {args.kd:.2f}"
                               f"{'  INV' if args.invert else ''}  {'' if args.port else '(no Mega)'}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"from front: {pan:+.2f}   h = set front here   r = go to front",
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            frames += 1
            if now - fps_t >= 2.0:
                if args.headless:
                    print(f"{frames / (now - fps_t):5.1f} fps  {status:9s}  DM:{speed:4d}  from front {pan:+.2f}",
                          flush=True)
                fps_t, frames = now, 0
            if frames % 2 == 0:                 # every other frame: plenty for watching
                for screen in screens:
                    screen.show(frame)
            if args.headless:
                continue
            cv2.imshow("Dome tracker PoC", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif key == ord(" "):
                paused = not paused
            elif key == ord("i"):
                args.invert = not args.invert
            elif key == ord("+"):
                args.max = min(args.max + 5, 80)
            elif key == ord("-"):
                args.max = max(args.max - 5, args.min)
            elif key == ord("]"):
                args.min = min(args.min + 2, args.max)
            elif key == ord("["):
                args.min = max(args.min - 2, 0)
            elif key == ord("."):
                args.kd = min(args.kd + 0.05, 1.5)
            elif key == ord(","):
                args.kd = max(args.kd - 0.05, 0.0)
            elif key == ord("h"):
                pan = 0.0
                returning = False
            elif key == ord("r"):
                last_face_t = 0.0
                returning = abs(pan) > HOME_BAND
    except KeyboardInterrupt:
        pass
    finally:
        mega.close()
        log.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
