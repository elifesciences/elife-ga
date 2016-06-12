#!/bin/bash
set -e # everything must succeed.
source .activate-venv.sh
pip install -r requirements.txt
