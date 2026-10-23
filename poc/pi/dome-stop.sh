#!/bin/sh
# Desktop shortcut "Parar Dome Tracker": the dome stops and stays still until the next start
# (or the next boot).
pkill -f "chromium.*localhost:8080"
sudo -n systemctl stop dome-tracker
