#!/bin/bash
set -e
module=''
if [ ! -z "$@" ]; then
    module=".$@"
fi
green --run-coverage -vv elife_ga_metrics.test"$module"

# is only run if tests pass
covered=$(coverage report | grep TOTAL | awk '{print $6}' | sed 's/\...%//')
if [ $covered -le 65 ]; then
    echo
    echo "FAILED this project requires at least 65% coverage"
    echo
    exit 1
fi

coverage html
