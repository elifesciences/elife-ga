#!/bin/bash
set -e # everything must pass

echo "reloading virtualenv"
rm -rf ./venv/
source install.sh

# upgrade all deps to latest version
pip install pip-review
pip-review --pre # preview the upgrades
echo "[any key to continue, ctrl-c to cancel ...]"
read -p "$*"
pip-review --auto --pre # update everything

# test
source .lint.sh
source .test.sh

# write out new requirements file so we can diff em
pip freeze > updated-requirements.txt
echo "wrote 'updated-requirements.txt'"
