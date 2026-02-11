#!/bin/sh
# run various linters
set -e
echo "formatting..."
python -m ruff format azuretests tests
echo "sorting import with ruff..."
python -m ruff check azuretests tests --fix --show-fixes
# run lint
sh scripts/lint.sh
