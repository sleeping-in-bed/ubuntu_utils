FROM container_dev:latest
COPY --chown=${USER_NAME}:${USER_NAME} requirements ./requirements
RUN sudo pip install --no-cache-dir -r requirements/dev.txt
