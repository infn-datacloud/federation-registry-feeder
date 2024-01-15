# Create requirements.txt from poetry dependencies
FROM python:3.8 AS requirements

WORKDIR /tmp

RUN pip install poetry

# Copy poetry.lock* in case it doesn't exist in the repo
COPY ./pyproject.toml ./poetry.lock* /tmp/

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
ENV INSTALL_CMD="poetry export -f requirements.txt --output requirements.txt --without-hashes"
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then ${INSTALL_CMD} --dev ; else ${INSTALL_CMD} ; fi"


# Stage used for development in containers
FROM python:3.8 AS development

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

# Create a user with the given name, UID and GID 
RUN groupadd --gid ${USER_GID} ${USERNAME} && \
    useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}

# Add the user to the sudoers, to allow to execute commands 
# requiring sudoers permissions (such as apt install).
RUN mkdir -p /etc/sudoers.d/ && \
    echo ${USERNAME} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USERNAME} && \
    chmod 0440 /etc/sudoers.d/${USERNAME}

# Set current user
USER ${USERNAME}

# Add here the commands specific for your image
WORKDIR /code/

COPY --from=requirements /tmp/requirements.txt /code/requirements.txt

# Upgrade pip and install requirements
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app


# Stage used in production
FROM python:3.8 AS cron-job

# Updating packages and installing cron
RUN apt-get update && apt-get -y install cron && apt-get clean

COPY --from=requirements /tmp/requirements.txt /app/requirements.txt
COPY src /app/src

ARG PROVIDERS_CONF_DIR=/providers-conf
ENV PROVIDERS_CONF_DIR=${PROVIDERS_CONF_DIR}

# Add crontab file in the cron directory
# and give execution rights on the cron job
COPY crontab /etc/cron.d/federation-registry-feeder-cron
RUN chmod 0644 /etc/cron.d/federation-registry-feeder-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Run the command on container startup
CMD cron && tail -f /var/log/cron.log