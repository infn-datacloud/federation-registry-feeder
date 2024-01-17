# Federation Registry Feeder

This python script populates the [Federation Registry](https://github.com/indigo-paas/federation-registry.git) through the REST API provider by that service.

In production mode, a cron job executes this script at a fixed frequency.

It is a [docker](https://www.docker.com/) based application.

## What the script does

<!-- It reads from a set of yaml files the provider configurations to load; it collects and pre-elaborates the data to send to the Federation Registry. For each provider, if it does not already exist, the script executes a POST request; if the provider already exists, the script executes a PUT request forcing the update of new values and relationships. For no more tracked providers it executes a DELETE request.

For each project, open the connection with the resource provider n times, one for each region to look for quotas, flavors, images and networks ot has access on the services supplied by that specific region. It filters images and flavors saving only active ones. Moreover it considers only images and networks matching any of the specified input tags. -->

# Installation and Usage

## Download the project

Clone this repository and move inside the project top folder.

```bash
git clone https://github.com/indigo-paas/federation-registry-feeder.git
cd federation-registry-feeder
```

## Production deployment

### Requirements

You need to have `docker` installed on your system and a running `federation-registry` instance.

<!-- In idle mode, the application uses at least 1.2 GiB of memory space and the `gunicorn` service starts 25 processes (PIDS).

A database with about 20000 entities occupies 500MB of disk space.

> These details can be retrieved running `docker stats` on the host machine and running `du -hs <path-to>/data` on the machine hosting the database. -->

# Run the script

In production mode you should run the application using the dedicated image [indigopaas/federation-registry-feeder](https://hub.docker.com/r/indigopaas/federation-registry-feeder) available on DockerHub.

The command to start the application inside a container is:

```bash
docker run -d -v ./providers-conf:/providers-conf -v /var/run/docker.sock:/var/run/docker.sock indigopaas/federation-registry-feeder
```

The previous command binds the host's **providers-conf** folder (in the project top level) to the container's **/providers-conf** directory. The command is not complete! **The service will not work until you correctly set the environment variables described in following**.

The application requires the following persistent volumes:

- **/providers-conf**: folder with the yaml files with the federated providers configurations.
- **/var/run/docker.sock**: docker socket used to connect to the docker daemon from inside the container.

It uses environment variables to configure the connection with the federation-registry service and with the providers to federate. You can pass these variables as arguments when starting the container. In the following table we list all the environment variables that can be passed to the command.

| Name                        | Mandatory | Description                                                                                                                                                                                                                             | Default value                                                                          |
| --------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `FEDERATION_REGISTRY_URL`   | x         | The federation-registry base URL. The script uses this value to build the endpoints to hit to update the service database. **A default value if provided to simplify development environment start up.**                                | http://localhost:8000                                                                  |
| `BLOCK_STORAGE_VOL_LABELS`  | x         | List of the volume type labels accepted. **The project starts also if this variable is not set but ...**                                                                                                                                | []                                                                                     |
| `PROVIDERS_CONF_DIR`        |           | Path to the directory containing the yaml files with the federated provider configurations. In production mode, it depends on were you mount this folder. **A default value if provided to simplify development environment start up.** | ./providers-conf (when working locally), /providers-conf (when using the docker image) |
| `OIDC_AGENT_CONTAINER_NAME` |           | Name of the container with the oidc-agent service instance. **A default value if provided to simplify development environment start up.**                                                                                               | federation-registry-feeder-oidc-agent-1                                                |
| `FLAVORS`                   |           | Flavors API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                           | v1                                                                                     |
| `IDENTITY_PROVIDERS`        |           | Identity providers API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                | v1                                                                                     |
| `IMAGES`                    |           | Images API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                            | v1                                                                                     |
| `LOCATIONS`                 |           | Locations API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                         | v1                                                                                     |
| `NETWORK`                   |           | Networks API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                          | v1                                                                                     |
| `PROJECTS`                  |           | Projects API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                          | v1                                                                                     |
| `PROVIDERS`                 |           | Providers API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                         | v1                                                                                     |
| `BLOCK_STORAGE_QUOTAS`      |           | Block storage quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                              | v1                                                                                     |
| `COMPUTE_QUOTAS`            |           | Compute quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                    | v1                                                                                     |
| `NETWORK_QUOTAS`            |           | Network quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                    | v1                                                                                     |
| `REGIONS`                   |           | Regions API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                           | v1                                                                                     |
| `BLOCK_STORAGE_SERVICES`    |           | Block storage services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                            | v1                                                                                     |
| `COMPUTE_SERVICES`          |           | Compute services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                  | v1                                                                                     |
| `IDENTITY_SERVICES`         |           | Identity services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                 | v1                                                                                     |
| `NETWORK_SERVICES`          |           | Network services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                  | v1                                                                                     |
| `SLAS`                      |           | SLAs API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                              | v1                                                                                     |
| `USER_GROUPS`               |           | User groups API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                                                       | v1                                                                                     |

Some of these variables are not mandatory. If not specified they will use the default value.

You can also create a `.env` file with all the variables you want to override. Here an example overriding all variables

```bash
# .env

FEDERATION_REGISTRY_URL=https://fed-reg.it/
BLOCK_STORAGE_VOL_LABELS=["first", "second"]
PROVIDERS_CONF=/providers-config
OIDC_AGENT_CONTAINER_NAME=fed-reg-feeder-oidc-1

FLAVORS=v1
IDENTITY_PROVIDERS=v1
...
```

> The **providers-conf** folder, in the project top level, is not tracked by git and can be used to contain all yaml files with the federated providers configurations. Alternatively you can mount your another volume into the same container directory, or you can change also the container's directory. If you change the container's folder name, you must consistently change the `PROVIDERS_CONF_DIR` environment variable.

### Ancillary services

To correctly work, the application requires a running `federation-registry` service instance.

If you don't have an already running instance, we suggest to deploy your instance using the [indigopaas/federation-registry](https://hub.docker.com/r/indigopaas/federation-registry) docker image available on DockerHub.

> The service instance needs a `neo4j` database instance with the **apoc** extension. Look at the [federation-registry documentation](https://github.com/indigo-paas/federation-registry) for more information about it.

It also needs a running `oidc-agent` service instance. **In fact you have to register a client for each trusted identity provider in any yaml files.** When registering a client you must use a user having access to every project defined in the yaml files. To have write access to the `federation-registry` instance ,**this user must be associated to one of the emails defined in the `federation-registry` `ADMIN_EMAIL_LIST` env variable, and it's hosting identity provider must be in the `TRUSTED_IDP_LIST`.**

If you don't have an already running instance, we suggest to deploy your instance using the [opensciencegrid/oidc-agent](https://hub.docker.com/r/opensciencegrid/oidc-agent) docker image available on DockerHub.

> When using this image remember to set `platform: linux/amd64`.

If you are using a container run the following command to register a new client using the oidc-agent inside that container. The provided scopes are not mandatory.

```
docker exec <oidc-agent-container-name> \
    oidc-gen \
    --flow device \
    --iss <issuer-url> \
    --dae <device-code-url> \
    --scope="openid profile offline_access email" \
    <config-name>
```

Once the service responds, move to the received link and authenticate using the credentials of the user with special privileges defined before. Once you have authorized service to access to user information the procedure will conclude.

Here an example using INFNCloud IAM:

```
docker exec federation-registry-feeder-oidc-agent-1 \
    oidc-gen \
    --flow device \
    --iss https://iam.cloud.infn.it/ \
    --dae https://iam.cloud.infn.it/devicecode \
    --scope="openid profile offline_access email" \
    infncloud
```

# Developers

> This repository makes use of githooks. To enable them install [pre-commit](https://pre-commit.com/) and run the `pre-commit install` command.

## Running

To start the service in development mode using docker compose type:

```bash
docker compose up -f docker-compose.yml -f docker-compose.override.yml up -d
```

otherwise, to start the service locally in development mode, look at the `README.md` in each subfolder.
