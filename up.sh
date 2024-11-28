#!/bin/bash
source .env
python3 ./.compose/compose.py -d "$@"
docker compose exec "$SERVICE" /bin/bash -c 'echo $PYCHARM_KEY' | xclip -selection clipboard
docker compose exec "$SERVICE" pycharm
