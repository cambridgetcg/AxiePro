#!/bin/bash
# Build Lambda Layer
# This script creates a Lambda layer with Python dependencies

set -e

LAYER_DIR="$(dirname "$0")"
cd "$LAYER_DIR"

echo "Building Lambda layer..."

# Clean up
rm -rf python/
mkdir -p python/

# Install dependencies
pip install -r requirements.txt -t python/ --platform manylinux2014_x86_64 --only-binary=:all:

# Clean up unnecessary files
find python/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find python/ -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find python/ -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

echo "Lambda layer built successfully!"
echo "Layer size: $(du -sh python/)"
