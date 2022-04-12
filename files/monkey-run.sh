#!/bin/bash
set -e # Exit script if any command fail

cd "$(dirname "$0")/.."
pipenv run python monkey.py
