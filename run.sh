#!/bin/bash
# Returns the daily views and downloads for the last day.
set -e
source install.sh
python elife_ga_metrics/core.py
