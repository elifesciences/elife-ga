#!/bin/bash
source install.sh > /dev/null
pylint2 -E elife_ga_metrics/*.py
python -m unittest --verbose --failfast --catch elife_ga_metrics.test.tests
