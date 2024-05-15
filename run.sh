#!/bin/bash

if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not use 'sudo' or 'root' to run this script"
else
    sudo apt update
    sudo apt install -y rabbitmq-server python3-pip
    sudo pip install --no-cache-dir psplpy==1.0.0 pika

    gnome-terminal -- bash -c 'python3 -c "from framework import *; UserProcess(user_result_mark, user_mark)"; exec bash'
    sudo python3 main.py
fi
exec bash
