#!/bin/bash
set -e
source install.sh
python -c "from elife_ga_metrics import bulk; bulk.regenerate_results('ga:82618489');"
