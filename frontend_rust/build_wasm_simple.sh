#!/bin/bash
set -e

# Build the WASM version of the Portfolio Optimizer frontend
echo "Building WASM version of Portfolio Optimizer..."

# Check if wasm32 target is installed
if ! rustup target list | grep -q "wasm32-unknown-unknown"; then
    echo "Adding wasm32-unknown-unknown target..."
    rustup target add wasm32-unknown-unknown
fi

# Check if wasm-bindgen-cli is installed
if ! command -v wasm-bindgen &> /dev/null; then
    echo "Installing wasm-bindgen-cli..."
    cargo install wasm-bindgen-cli
fi

# Create dist directory if it doesn't exist
mkdir -p dist

# Create a simple WASM example
cat > wasm_example.rs << EOL
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn greet(name: &str) -> String {
    format!("Hello, {}! This is a WASM test.", name)
}
EOL

# Compile the WASM example
echo "Compiling WASM example..."
rustc --target wasm32-unknown-unknown -O --crate-type=cdylib wasm_example.rs -o dist/example.wasm

# Generate JavaScript bindings
echo "Generating JavaScript bindings..."
wasm-bindgen dist/example.wasm --out-dir dist --no-typescript

# Create a simple HTML file to test the WASM
cat > dist/index.html << EOL
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>WASM Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        #result {
            margin-top: 20px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WebAssembly Test</h1>
        <p>This is a simple test of WebAssembly functionality.</p>
        <input type="text" id="name" placeholder="Enter your name" value="Portfolio Optimizer">
        <button id="greet-button">Greet</button>
        <div id="result"></div>
    </div>

    <script type="module">
        import init, { greet } from './example.js';

        async function run() {
            await init();
            
            document.getElementById('greet-button').addEventListener('click', () => {
                const name = document.getElementById('name').value;
                const result = greet(name);
                document.getElementById('result').textContent = result;
            });
        }

        run();
    </script>
</body>
</html>
EOL

echo "WASM build completed successfully! Output is in the ./dist directory."
echo "To test locally, serve the dist directory with a web server."
echo "To deploy to GCP Cloud Storage:"
echo "gcloud storage cp -r dist/* gs://<your-bucket-name>"