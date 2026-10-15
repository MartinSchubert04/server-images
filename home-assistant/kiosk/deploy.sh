#!/bin/sh
# Build the single-view kiosk dashboard and leave it at /local/kiosk/kd.json
# (http://<ha>/local/kiosk/kd.json) so it can be saved into HA. See HANDOFF.md
# ("Deploy") for the save step and remember to delete kd.json afterwards.
# Run from Git Bash on MRTN-SERVER.
set -e
cd "$(dirname "$0")"
MSYS_NO_PATHCONV=1 docker cp dashboard.yaml homeassistant:/tmp/kd.yaml
MSYS_NO_PATHCONV=1 docker cp build_dashboard.py homeassistant:/tmp/build_dashboard.py
MSYS_NO_PATHCONV=1 docker exec homeassistant python3 /tmp/build_dashboard.py /tmp/kd.yaml /config/www/kiosk/kd.json
MSYS_NO_PATHCONV=1 docker exec homeassistant rm /tmp/kd.yaml /tmp/build_dashboard.py
