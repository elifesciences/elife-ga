#!/bin/bash
# Regenerates all views and downloads since we started 
# capturing them.
# Call this whenever the query or table changes or when
# code changes affect the results output.
set -e
source install.sh
python -c "import os; from elife_ga_metrics import bulk; bulk.regenerate_results(os.environ['GA_TABLE']);"
