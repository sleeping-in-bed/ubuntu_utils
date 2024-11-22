FROM remote_pycharm:latest
COPY --chown=$USER_NAME:$USER_NAME requirements.txt .
RUN sudo apt update && sudo apt install -y rabbitmq-server && sudo apt clean
RUN sudo pip install --no-cache-dir -r requirements.txt
RUN git config --global user.email "a@a.com" &&\
    git config --global user.name "a" &&\
    git config --global core.autocrlf input
