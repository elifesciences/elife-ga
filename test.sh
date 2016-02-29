#!/bin/bash
set -e
source install.sh
pylint -E elife_ga_metrics/*.py elife_ga_metrics/test/*.py \
    --ignored-classes=Resource # google-api-python-client.discovery.Resource - dynamicly set attributes
coverage run --source='elife_ga_metrics/' -m unittest discover elife_ga_metrics.test -p '*_tests.py'
coverage report
