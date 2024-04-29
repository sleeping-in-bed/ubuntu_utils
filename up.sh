#!/bin/bash
source .env
docker network create "$MYBRIDGE"
python3 compose.py -d "$@"
docker compose exec "$SERVICE" /bin/bash -c 'echo $PYCHARM_KEY' | xclip -selection clipboard
docker compose exec "$SERVICE" pycharm
