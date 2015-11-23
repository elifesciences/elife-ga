#!/bin/bash
# Returns daily and monthly views and downloads 
# for the last week
set -e
source install.sh
python elife_ga_metrics/bulk.py
