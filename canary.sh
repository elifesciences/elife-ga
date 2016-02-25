#!/bin/bash

# everything must pass
set -e

# reload the virtualenv
rm -rf venv/
source install.sh

# upgrade all deps to latest version
pip install pip-review
pip-review --pre # preview the upgrades
echo "[any key to continue ...]"
read -p "$*"
pip-review --auto --pre # update everything
pylint -E elife_ga_metrics/*.py elife_ga_metrics/test/*.py
python -m unittest discover --verbose --failfast --catch --start-directory elife_ga_metrics/test/ --pattern "*.py"
