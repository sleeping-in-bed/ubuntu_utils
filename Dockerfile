# This file was automatically generated by DynamicCompose, and can be safely deleted, but do not edit it or remove this comment.
FROM remote_pycharm:latest
COPY --chown=$USER_NAME:$USER_NAME requirements.txt .
RUN sudo apt update && sudo apt install -y rabbitmq-server && sudo apt clean
RUN sudo pip install --no-cache-dir -r requirements.txt
RUN git config --global user.email "you@example.com" &&\
    git config --global user.name "Your Name"
