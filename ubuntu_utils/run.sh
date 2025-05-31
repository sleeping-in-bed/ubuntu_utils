#!/bin/bash

if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not use 'sudo' or 'root' to run this script"
else
    sudo python3 ./main.py &
    sleep 0.5
    python3 -c "from framework.process import UserProcess; UserProcess()"
fi
