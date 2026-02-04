#!/bin/bash
set -e

echo "==================================="
echo "Running tests with pytest in Docker"
echo "==================================="

# Build and run tests
docker-compose -f docker-compose.test.yml build test
docker-compose -f docker-compose.test.yml run --rm test

echo ""
echo "==================================="
echo "Test run completed!"
echo "==================================="
