# Federation Registry Feeder

This python script populates the [Federation Registry](https://github.com/indigo-paas/federation-registry.git) through the REST API provider by that service.

It uses [oidc-agent](https://indigo-dc.gitbook.io/oidc-agent/) to generate the tokens to use to perform authenticated requests on both the `federation-registry` and the resource providers.

In production mode the application is meant to be used with [docker](https://www.docker.com/) and another scheduler service such as [ofelia](https://github.com/mcuadros/ofelia) to execute the script at fixed intervals.

# Script logic

It reads from a set of yaml files the provider configurations to load. **These files must have the `.config.yaml` extension.**

In parallel, for each openstack provider defined in a `.config.yaml` file, the script opens `p*r` parallel connections with the resource provider where `p` is the number of projects and `r` is the number of regions defined for that provider.

For each connection (which corresponds to a specific couple project-region), the script looks for the quotas, flavors, images and networks accessible on the services supplied by that specific region. It filters images and flavors marked as _active_. Moreover it considers only images and networks matching any of the specified input tags.

Once it has collected the data from the providers, pre-elaborates and organizes the data to send to the Federation Registry.

For each provider, if it does not already exist, the script executes a POST request; if the provider already exists, the script executes a PUT request forcing the update of new values and relationships. For no more tracked providers it executes a DELETE request.

# Production deployment

## Requirements

You need to have `docker` installed on your system and a running `federation-registry` instance.

In idle mode, the application uses at least 10 MiB of memory space.

Currently we don't have an estimate of the disk space used by the app.

> These details can be retrieved running `docker stats` on the host machine and running `du -hs <path-to>/data` on the machine hosting the database.

## Start up the main service

In production mode you should run the application using the dedicated image [indigopaas/federation-registry-feeder](https://hub.docker.com/r/indigopaas/federation-registry-feeder) available on DockerHub.

The application requires the following persistent volumes:

- **/providers-conf**: folder with the `.config.yaml` files with the federated providers configurations. Read only mode.
- **/var/run/docker.sock**: docker socket used to connect to the docker daemon from inside the container. Read only mode.

It uses **environment variables** to configure the connection with the `federation-registry` service and with the `oidc-agent` service in charge of continuously generate the authorization tokens. You can pass these variables as arguments when starting the container.

The command to correctly start the application inside a container is the environment variables default is:

```bash
docker run -d -v ./providers-conf:/providers-conf:ro -v /var/run/docker.sock:/var/run/docker.sock:ro indigopaas/federation-registry-feeder
```

The previous command binds the host's **providers-conf** folder (in the project top level) to the container's **/providers-conf** directory. The application will try to connect to the `federation-registry` instance located at http://localhost:8000; it will try to use the docker container named `federation-registry-feeder-oidc-agent-1` to generate the authorization tokens.

In the following table we list all the environment variables that can be passed to the command using the `-e` param.

- `FEDERATION_REGISTRY_URL`
  - **description**: The federation-registry base URL. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: YES
  - **default**: http://localhost:8000. _A default value if provided to simplify development environment start up._
- `OIDC_AGENT_CONTAINER_NAME`
  - **description**: Name of the container with the oidc-agent service instance. It depends on the value of `container_name` of the `oidc-agent` docker service to use.
  - **type**: string
  - **mandatory**: YES
  - **default**: federation-registry-feeder-oidc-agent-1. _A default value if provided to simplify development environment start up._
- `BLOCK_STORAGE_VOL_LABELS`
  - **description**: List of the volume type labels accepted. **The project starts also if this variable is not set but ...**
  - **type**: List of string
  - **mandatory**: YES
  - **default**: []. _A default value if provided to simplify development environment start up._
- `PROVIDERS_CONF_DIR`
  - **description**: Path to the directory containing the `.config.yaml` files with the federated provider configurations. **In production mode, it depends on were you mount this folder. Hopefully this should not be changed.**
  - **type**: path
  - **mandatory**: NO
  - **default**: /providers-conf. _in development mode, the default value is **./providers-conf**._
- `FLAVORS`
  - **description**: Flavors API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `IDENTITY_PROVIDERS`
  - **description**: Identity providers API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `IMAGES`
  - **description**: Images API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `LOCATIONS`
  - **description**: Locations API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `NETWORKS`
  - **description**: Networks API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `PROJECTS`
  - **description**: Projects API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `PROVIDERS`
  - **description**: Providers API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `BLOCK_STORAGE_QUOTAS`
  - **description**: Block storage quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `COMPUTE_QUOTAS`
  - **description**: Compute quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `NETWORK_QUOTAS`
  - **description**: Network quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `REGIONS`
  - **description**: Regions API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `BLOCK_STORAGE_SERVICES`
  - **description**: Block storage services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `COMPUTE_SERVICES`
  - **description**: Compute services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `IDENTITY_SERVICES`
  - **description**: Identity services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `NETWORK_SERVICES`
  - **description**: Network services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `SLAS`
  - **description**: SLAs API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1
- `USER_GROUPS`
  - **description**: User groups API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.
  - **type**: URL
  - **mandatory**: NO
  - **default**: v1

You can also create a `.env` file with all the variables you want to override. Here an example:

```bash
# .env

FEDERATION_REGISTRY_URL=https://fed-reg.it/
OIDC_AGENT_CONTAINER_NAME=fed-reg-feeder-oidc-1
BLOCK_STORAGE_VOL_LABELS=["first", "second"]

FLAVORS=v1
IDENTITY_PROVIDERS=v1
...
```

> The **providers-conf** folder, in the project top level, is not tracked by git and can be used to contain all yaml files with the federated providers configurations. Alternatively you can bind another folder into the same container directory.

> It is possible to change also the container's directory name but it is **highly** discouraged. If you change the container's folder name, you must consistently change the `PROVIDERS_CONF_DIR` environment variable.

## Ancillary services

### Federation-Registry

To correctly work, the application requires a running `federation-registry` service instance.

If you don't have an already running instance, we suggest to deploy your instance using the [indigopaas/federation-registry](https://hub.docker.com/r/indigopaas/federation-registry) docker image available on DockerHub.

> The service instance needs a `neo4j` database instance with the **apoc** extension. Look at the [federation-registry documentation](https://github.com/indigo-paas/federation-registry) for more information about it.

### OIDC-Agent

It also needs a running `oidc-agent` service instance. **In fact you have to register a client for each trusted identity provider in any yaml files.**

When registering a client:

- Choose a user having access to every project defined in the `.config.yaml` files. This is essential to have read access to the target projects.
- The chosen user must be associated to one of the emails defined in the `federation-registry` `ADMIN_EMAIL_LIST` env variable, and it's hosting identity provider must be in the `TRUSTED_IDP_LIST`. This is essential to have write access to the `federation-registry` instance.

If you don't have an already running instance, we suggest to deploy your instance using the [opensciencegrid/oidc-agent](https://hub.docker.com/r/opensciencegrid/oidc-agent) docker image available on DockerHub.

> When using this image remember to set `platform: linux/amd64`. We also suggest to bind a volume to the container `/root/.oidc-agent` folder to not loose your oidc configurations.

If you are using a container run the following command to register a new client using the oidc-agent inside that container. The provided scopes are not mandatory.

```bash
docker exec <oidc-agent-container-name> \
    oidc-gen \
    --flow device \
    --iss <issuer-url> \
    --dae <device-code-url> \
    --scope="openid profile offline_access email" \
    <config-name>
```

Once the service responds, move to the received link and authenticate using the credentials of the user with special privileges defined before. Once you have authorized service to access to user information the procedure will conclude.

To manually retrieve the token you can use the following command

```bash
docker exec <oidc-agent-container-name> oidc-token <config-name>
```

On service start up, since the script does not use the <config-name> but the issuer url, you have to manually add again your configurations. For each configuration run the following command:

```bash
docker exec <oidc-agent-container-name> oidc-add <config-name>
```

Here an example using INFN Cloud IAM:

```bash
# Create a new INFN CLoud IAM configuration.
docker exec federation-registry-feeder-oidc-agent-1 \
    oidc-gen \
    --flow device \
    --iss https://iam.cloud.infn.it/ \
    --dae https://iam.cloud.infn.it/devicecode \
    --scope="openid profile offline_access email" \
    infncloud

# Retrieve a valid token for the INFN CLoud IAM configuration.
docker exec federation-registry-feeder-oidc-agent-1 oidc-token infncloud

# Add again the INFN CLoud IAM configuration on service start-up.
docker exec federation-registry-feeder-oidc-agent-1 oidc-token infncloud
```

### Job Scheduler

As previously said you need a container job scheduler to execute the script contained in the docker image at fixed intervals.

Here, we suggest to use [ofelia](https://github.com/mcuadros/ofelia) and we provide an example configuration for a `docker-compose.yaml`.

```yaml
# docker-compose.yaml
version: "3"

services:
  federation-registry-feeder:
    image: indigopaas/federation-registry-feeder
    container_name: feeder
      - FEDERATION_REGISTRY_URL=http://host.docker.internal:8000/
    volumes:
      - ./providers-conf:/providers-conf:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    # Infinite loop to keep container live doing nothing
    command: bash -c "while true; do sleep 1; done"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    labels:
      ofelia.enabled: "true"
      ofelia.job-exec.feed.schedule: "@every 1m"
      ofelia.job-exec.feed.command: "python /app/src/main.py"
      ofelia.job-exec.feed.save-folder: /var/log
      ofelia.job-exec.feed.no-overlap: true

  ofelia:
    image: mcuadros/ofelia:latest
    container_name: feeder-job-scheduler
    depends_on:
      - federation-registry-feeder
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - feeder-logs:/var/log
    command: daemon --docker

volumes:
  feeder-logs:
```

# Developers

## Installation

Clone this repository and move inside the project top folder.

```bash
git clone https://github.com/indigo-paas/federation-registry-feeder.git
cd federation-registry-feeder
```

## Setting up environment

Developers can launch the project locally or using containers.

In both cases, developers need a `federation-registry` service and an `oidc-agent` service. Both can be started using docker.

> Remember that the `federation-registry` needs a `neo4j` database instance.

### Local Development (suggested for Linux users)

Requirements:

- Docker (to start `neo4j`, `federation-registry` and `oidc-agent` services)
- Poetry

If you don't have an already running instance, we suggest to start the `neo4j` database, the `federation-registry` application and the `oidc-agent` service using the `docker-compose.yml` located inside the `.devcontainer` folder.

```bash
cd .devcontainer
docker compose up -d db oidc-agent registry
```

or

```bash
docker compose -f .devcontainer/docker-compose.ymal up -d db oidc-agent registry
```

Then, using [poetry](https://python-poetry.org/), developers can install the libraries needed to start the python app and the tools to manage the code versioning, linting and formatting.

We suggest to configure poetry to create the virtual environment inside the project folder to help VSCode environment discover.

```bash
poetry config virtualenvs.in-project true
poetry install
```

The previous commands should be execute just the first time. You shall run the install step again when downloading a newer version of the project.

To activate the virtual environment you can run the following command:

```bash
poetry shell
```

### VSCode Dev-Container (suggested for MacOS users)

Requirements:

- Docker

Using VSCode you can open the entire folder inside the provided development container. The `docker-compose.yaml`, located in the `.devcontainer` folder, starts a `neo4j` database, a `federation-registry` application instance, an `oidc-agent` service and a python based container with all the production and development libraries. The development container use a non root user **vscode** with sudoers privileges, it has access to the host docker service and has a set of VSCode extensions already installed.

> The _docker-outside-docker_ extension allows developers to connect to the docker daemon service running on their host from inside the container.

> If you are using `docker compose` instead of `docker-compose`. Verify that in the VSCode User Settings `Dev › Containers: Docker Compose Path` you are using **docker compose** instead of **docker-compose**.

## Start up the app

To run the application in development mode developers can use the following command from the project top folder:

```bash
python src/main.py
```

Alternatively, users using VSCode, can use the `launch.json` file provided in the `.vscode` folder to run the application. The `Python: Population script` configuration will execute the previous command.

### Automatic tests

Automatic tests have been implemented using the `pytest` and `pytest-cases` library.

To run the test suite you can run, from the project top folder, the following command:

```bash
pytest
```

## Tools

This repository makes use of githooks such as [pre-commit](https://pre-commit.com/). This tools is configured to prevent to commit code with syntax errors or not well formatted.

Tests have been developed using [pytest](https://docs.pytest.org/en/latest/) and [pytest-cases](https://smarie.github.io/python-pytest-cases/). Coverage configuration details are defined in the `.coveragerc` file.

Formatting and linting is made through [ruff](https://docs.astral.sh/ruff/). Ruff configuration is defined in the `pyproject.toml` file and the `pre-commit` githook runs the linting and formatting on the code. The linting and the formatting can be manually launched on the project. Look at the online documentation for the commands syntax.

To run locally the github actions developers can use [act](https://github.com/nektos/act).

<!-- > In order for the **test-analysis** job to work, users must define locally the **SONAR_TOKEN** env variable.-->

## Build the image

A github action build and push a new docker image version on dockerhub with the name [indigopaas/federation-registry-feeder](https://hub.docker.com/r/indigopaas/federation-registry-feeder) on each push or merge on the main branch. To have a local build on your PC you can run this command:

```bash
docker build -t indigopaas/federation-registry-feeder .
```
