#!/bin/sh
# Desktop shortcut "R2 Dome Tracker": start the tracker if it is stopped, then show its picture
# full screen (Alt+F4 closes the picture; the tracker keeps running).
systemctl is-active --quiet dome-tracker || sudo -n systemctl start dome-tracker
until curl -s -o /dev/null http://localhost:8080/; do sleep 1; done
pgrep -f "chromium.*localhost:8080" >/dev/null && exit 0
exec chromium --ozone-platform=wayland --kiosk --noerrdialogs --disable-infobars --no-first-run \
    --password-store=basic http://localhost:8080/
