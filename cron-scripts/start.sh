#!/bin/bash

scriptPath=$(dirname "$(readlink -f "$0")")

# Export all env variables to .env.sh
printenv | sed 's/^\(.*\)$/export \1/g' > ${scriptPath}/.env.sh
chmod +x ${scriptPath}/.env.sh

# Create the log file to be able to run tail
cron && tail -f $LOG_FILE
