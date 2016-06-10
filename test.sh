#!/bin/bash
set -e
source install.sh
pylint -E elife_ga_metrics/*.py elife_ga_metrics/test/*.py \
    --ignored-classes=Resource # google-api-python-client.discovery.Resource - dynamicly set attributes
module=''
if [ ! -z "$@" ]; then
    module=".$@"
fi
green --run-coverage -vv elife_ga_metrics.test"$module"
