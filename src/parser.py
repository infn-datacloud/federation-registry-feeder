"""Command line arguments parser."""

import argparse
import logging

log_values = [i.lower() for i in logging._nameToLevel.keys()]

parser = argparse.ArgumentParser()
parser.add_argument(
    "-l",
    "--loglevel",
    default="warning",
    choices=log_values,
    help=f"Provide logging level. Valid values: {log_values}. \
        Example --loglevel debug, default=warning",
)
