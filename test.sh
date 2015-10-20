#!/bin/bash
source install.sh > /dev/null
pylint -E elife_ga_metrics/*.py
#python -m unittest --verbose --failfast --catch elife_ga_metrics.test
python -m unittest discover --verbose --failfast --catch --start-directory elife_ga_metrics/test/ --pattern "*.py"
