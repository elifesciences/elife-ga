#!/bin/bash
set -e
source install.sh
pylint -E elife_ga_metrics/*.py elife_ga_metrics/test/*.py \
    --ignored-classes=Resource # google-api-python-client.discovery.Resource - dynamicly set attributes
python -m unittest discover --verbose --failfast --catch --start-directory elife_ga_metrics/test/ --pattern "*.py"
