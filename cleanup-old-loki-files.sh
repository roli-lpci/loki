#!/usr/bin/env bash
set -euo pipefail

echo "Removing obsolete Loki directories/files..."

rm -rf \
    ui-tui \
    __MACOSX \
    website/build \
    docs.json \
    llms-full.txt

find . \
    -type d \( \
        -name '__pycache__' \
        -o -name '.pytest_cache' \
        -o -name '.mypy_cache' \
        -o -name '.ruff_cache' \
        -o -name '.coverage_cache' \
    \) \
    -prune -exec rm -rf {} +

find . \
    -type f \( \
        -name '*.pyc' \
        -o -name '*.pyo' \
        -o -name '.DS_Store' \
    \) \
    -delete

find . \
    -type d -name '*.egg-info' \
    -prune -exec rm -rf {} +

echo "Cleanup complete."
