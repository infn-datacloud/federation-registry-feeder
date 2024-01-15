# Federation Registry Feeder

This python script populates the [Federation Registry](https://github.com/indigo-paas/federation-registry.git) through the REST API provider by that service.

In production mode, a cron job executes this script at a fixed frequency.

It is a [docker](https://www.docker.com/) based application.

## What the script does

It reads from a set of yaml files the provider configurations to load; it collects and pre-elaborates the data to send to the Federation Registry. For each provider, if it does not already exist, the script executes a POST request; if the provider already exists, the script executes a PUT request forcing the update of new values and relationships. For no more tracked providers it executes a DELETE request.

For each project, open the connection with the resource provider n times, one for each region to look for quotas, flavors, images and networks ot has access on the services supplied by that specific region. It filters images and flavors saving only active ones. Moreover it considers only images and networks matching any of the specified input tags.

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
docker run -d indigopaas/federation-registry-feeder
```

The application requires the following persistent volumes:

-

It uses environment variables to configure the connection with the federation-registry service and with the providers to federate. You can pass these variables as arguments when starting the container. In the following table we list all the environment variables that can be passed to the command.

| Name                       | Mandatory | Description                                                                                                                                                                                              | Default value         |
| -------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `FEDERATION_REGISTRY_URL`  | x         | The federation-registry base URL. The script uses this value to build the endpoints to hit to update the service database. **A default value if provided to simplify development environment start up.** | http://localhost:8000 |
| `BLOCK_STORAGE_VOL_LABELS` | x         | List of the volume type labels accepted. **The project starts also if this variable is not set but ...**                                                                                                 | []                    |
| `WATCHER`                  | x         | User authorized to inspect projects details on all providers.                                                                                                                                            | null                  |
| `FLAVORS`                  |           | Flavors API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                            | v1                    |
| `IDENTITY_PROVIDERS`       |           | Identity providers API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                 | v1                    |
| `IMAGES`                   |           | Images API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                             | v1                    |
| `LOCATIONS`                |           | Locations API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                          | v1                    |
| `NETWORK`                  |           | Networks API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                           | v1                    |
| `PROJECTS`                 |           | Projects API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                           | v1                    |
| `PROVIDERS`                |           | Providers API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                          | v1                    |
| `BLOCK_STORAGE_QUOTAS`     |           | Block storage quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                               | v1                    |
| `COMPUTE_QUOTAS`           |           | Compute quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                     | v1                    |
| `NETWORK_QUOTAS`           |           | Network quotas API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                     | v1                    |
| `REGIONS`                  |           | Regions API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                            | v1                    |
| `BLOCK_STORAGE_SERVICES`   |           | Block storage services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                             | v1                    |
| `COMPUTE_SERVICES`         |           | Compute services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                   | v1                    |
| `IDENTITY_SERVICES`        |           | Identity services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                  | v1                    |
| `NETWORK_SERVICES`         |           | Network services API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                   | v1                    |
| `SLAS`                     |           | SLAs API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                               | v1                    |
| `USER_GROUPS`              |           | User groups API endpoint version to use. The script uses this value to build the endpoints to hit to update the service database.                                                                        | v1                    |

Some of these variables are not mandatory. If not specified they will use the default value.

You can also create a `.env` file with all the variables you want to override. Here an example overriding all variables

```bash
# .env

FEDERATION_REGISTRY_URL=https://fed-reg.it/
BLOCK_STORAGE_VOL_LABELS=["first", "second"]
WATCHER=test-watcher

FLAVORS=v1
IDENTITY_PROVIDERS=v1
...
```

### Ancillary services

To correctly work, the application requires a running `federation-registry` service instance.

If you don't have an already running instance, we suggest to deploy your instance using the [indigopaas/federation-registry](https://hub.docker.com/r/indigopaas/federation-registry) docker image available on DockerHub.

> The service instance needs a `neo4j` database instance with the **apoc** extension. Look at the [federation-registry documentation](https://github.com/indigo-paas/federation-registry) for more information about it.

# Developers

> This repository makes use of githooks. To enable them install [pre-commit](https://pre-commit.com/) and run the `pre-commit install` command.

## Running

To start the service in development mode using docker compose type:

```bash
docker compose up -f docker-compose.yml -f docker-compose.override.yml up -d
```

otherwise, to start the service locally in development mode, look at the `README.md` in each subfolder.
