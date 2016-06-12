#!/bin/bash
set -e
module=''
if [ ! -z "$@" ]; then
    module=".$@"
fi
green --run-coverage -vv elife_ga_metrics.test"$module"
