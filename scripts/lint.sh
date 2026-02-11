#!/bin/sh
# run various linters
set -e
echo "running ruff..."
python -m ruff format azuretests tests --check
python -m ruff check azuretests tests
echo "running mypy..."
python3 -m mypy --show-error-codes azuretests