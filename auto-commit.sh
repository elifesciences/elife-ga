#!/bin/bash

# commits any new JSON files and modifications to existing JSON files.
# intended to be run automatically by the CI server
# @author Luke Skibinski <l.skibinski@elifesciences.org>

set -e
git add output/*.json
# http://stackoverflow.com/questions/8123674/how-to-git-commit-nothing-without-an-error
git diff-index --quiet HEAD || git commit -m "automatic commit"
git push origin master
