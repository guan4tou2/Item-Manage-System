#!/bin/bash
set -e

echo "==================================="
echo "Running tests with uv (local)"
echo "==================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    pip install uv
fi

# Install dependencies
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt
uv pip install pytest pytest-cov pytest-mock pytest-flask pytest-env

# Run tests
echo ""
echo "Running tests..."
pytest -v --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "==================================="
echo "Test run completed!"
echo "Coverage report: htmlcov/index.html"
echo "==================================="
