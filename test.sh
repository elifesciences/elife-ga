#!/bin/bash
source install.sh > /dev/null
pylint2 -E elife_ga_metrics/*.py
