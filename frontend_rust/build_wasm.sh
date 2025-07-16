#!/bin/bash

# Build the WASM version of the Portfolio Optimizer frontend
echo "Building WASM version of Portfolio Optimizer..."

# Check if trunk is installed
if ! command -v trunk &> /dev/null; then
    echo "Installing trunk..."
    cargo install trunk
fi

# Check if wasm32 target is installed
if ! rustup target list | grep -q "wasm32-unknown-unknown"; then
    echo "Adding wasm32-unknown-unknown target..."
    rustup target add wasm32-unknown-unknown
fi

# Build the WASM version
echo "Running trunk build..."
trunk build --release

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Build successful! WASM artifacts are in the dist/ directory."
    echo "To deploy to GCP Cloud Storage:"
    echo "gcloud storage cp -r dist/* gs://<your-bucket-name>"
else
    echo "Build failed. Please check the error messages above."
fi