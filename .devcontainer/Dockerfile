# Create requirements.txt from poetry dependencies
FROM python:3.8 AS requirements

WORKDIR /tmp

RUN pip install poetry

# Copy poetry.lock* in case it doesn't exist in the repo
COPY ./pyproject.toml ./poetry.lock* /tmp/

# Allow installing dev dependencies to run tests
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --dev


# Stage used for development in containers
FROM python:3.8 AS devcontainer

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

# Create a user with the given name, UID and GID 
# Add the user to the sudoers, to allow to execute commands 
# requiring sudoers permissions (such as apt install or access host's docker service).
RUN groupadd --gid ${USER_GID} ${USERNAME} && \
    useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} && \
    apt-get update && \
    apt-get install -y sudo && \
    apt-get clean && \
    echo ${USERNAME} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USERNAME} && \
    chmod 0440 /etc/sudoers.d/${USERNAME}

# Set current user
USER ${USERNAME}

WORKDIR /code/

# Import requirements from production image
COPY --from=requirements /tmp/requirements.txt /code/requirements.txt

# Upgrade pip and install requirements
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt


COPY ./src /code/src

