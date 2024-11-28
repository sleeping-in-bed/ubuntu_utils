#!/bin/bash

if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not use 'sudo' or 'root' to run this script"
else
    output=$(echo $DISPLAY)
    if [ -z "$output" ]; then
        echo "Has not GUI"
    else
        gnome-terminal -- bash -c 'python3 ./src/run_user_process.py 1; exec bash'
        sudo python3 ./src/main.py
    fi
fi
exec /bin/bash
