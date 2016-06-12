#!/bin/bash
pylint -E elife_ga_metrics/*.py elife_ga_metrics/test/*.py \
    --ignored-classes=Resource # google-api-python-client.discovery.Resource - dynamicly set attributes
