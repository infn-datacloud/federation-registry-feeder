#!/bin/sh

scriptPath=$(dirname "$(readlink -f "$0")")
. "${scriptPath}/.env.sh"

# the docker-compose variables should be available here
/usr/local/bin/python /app/src/main.py >> $LOG_FILE 2>&1
