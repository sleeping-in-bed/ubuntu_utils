#!/usr/bin/env bash

if [ "$(id -u)" -eq 0 ]; then
    ORIG_USER="${SUDO_USER}"
else
    ORIG_USER="$(whoami)"
fi

PARENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo PARENT_DIR
TARGET_FILE="$PARENT_DIR/tmp/shared.json"
sudo rm -f "$TARGET_FILE"

code=$(cat <<EOF
from ubuntu_utils.commands import *

r.start()
try:
    $1
finally:
    r.close_all()
EOF
)
echo "$code"
echo "$code" | sudo $(which python3) &
sleep 1
sudo -u "$ORIG_USER" python3 -c "from ubuntu_utils.framework.process import UserProcess; UserProcess()"
