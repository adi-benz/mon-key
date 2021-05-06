#!/bin/bash
set -e # Exit script if any command fail

cd "$(dirname "$0")"
python3 main.py
