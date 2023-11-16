FROM airdock/python-poetry as requirements

WORKDIR /app/

# Copy poetry.lock* in case it doesn't exist in the repo
COPY ./pyproject.toml ./poetry.lock* /app/

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
ENV INSTALL_CMD="poetry export -f requirements.txt --output requirements.txt --without-hashes"
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then ${INSTALL_CMD} --dev ; else ${INSTALL_CMD} ; fi"


FROM python:latest as cron-job

# Updating packages and installing cron
RUN apt-get update && apt-get -y install cron

COPY --from=requirements /app/requirements.txt /app/requirements.txt
COPY src /app/src

# Add crontab file in the cron directory
# and give execution rights on the cron job
COPY crontab /etc/cron.d/federation-registry-population-script-cron
RUN chmod 0644 /etc/cron.d/federation-registry-population-script-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Run the command on container startup
CMD cron && tail -f /var/log/cron.log