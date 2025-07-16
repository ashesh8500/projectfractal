# Modular Structure for Portfolio Optimizer Frontend

This document outlines the modular structure of the Portfolio Optimizer frontend application, designed to be maintainable, extensible, and WASM-compatible.

## Directory Structure

```
frontend_rust/
├── src/
│   ├── api/                  # API communication layer
│   │   ├── client.rs         # gRPC client implementation
│   │   └── mod.rs
│   ├── components/           # Reusable UI components
│   │   ├── manager.rs        # Component management system
│   │   ├── mod.rs
│   │   └── ...               # Individual components
│   ├── models/               # Data models and state
│   │   ├── app_state.rs      # Application state
│   │   ├── messages.rs       # Message types for async communication
│   │   ├── performance.rs    # Performance metrics models
│   │   └── mod.rs
│   ├── ui/                   # UI implementation
│   │   ├── app.rs            # Main application UI
│   │   ├── portfolio.rs      # Portfolio management UI
│   │   ├── strategy.rs       # Strategy analysis UI
│   │   ├── charts.rs         # Chart rendering
│   │   ├── settings.rs       # Settings UI
│   │   └── mod.rs
│   ├── utils/                # Utility functions
│   │   ├── wasm.rs           # WASM-specific utilities
│   │   └── mod.rs
│   └── main.rs               # Application entry point
├── Cargo.toml                # Project dependencies
├── build.rs                  # Build script for proto compilation
└── index.html                # HTML entry point for WASM
```

## Module Responsibilities

### API Module

The `api` module handles all communication with the backend server:

- `client.rs`: Implements the gRPC client with platform-specific code for both native and WASM targets.

### Models Module

The `models` module contains all data structures and state management:

- `app_state.rs`: Defines the application state structure.
- `messages.rs`: Defines message types for async communication.
- `performance.rs`: Contains performance metrics data structures and calculation logic.

### UI Module

The `ui` module contains all UI-related code:

- `app.rs`: Main application UI implementation.
- `portfolio.rs`: Portfolio management UI components.
- `strategy.rs`: Strategy analysis UI components.
- `charts.rs`: Chart rendering components.
- `settings.rs`: Settings UI components.

### Components Module

The `components` module contains reusable UI components:

- `manager.rs`: Component management system.
- Various component implementations.

### Utils Module

The `utils` module contains utility functions:

- `wasm.rs`: WASM-specific utilities like console logging.

## Cross-Platform Compatibility

The application is designed to work on both native platforms and as a WebAssembly (WASM) application:

- Platform-specific code is isolated using `#[cfg(target_arch = "wasm32")]` attributes.
- The `api` module handles different gRPC client implementations for native and WASM targets.
- Async operations are handled differently based on the platform (tokio Runtime for native, wasm_bindgen_futures for WASM).

## Building and Running

### Native Build

```bash
cd frontend_rust
cargo run --release
```

### WASM Build

```bash
cd frontend_rust
trunk build --release
```

The WASM build will generate files in the `dist` directory that can be deployed to a web server.

## Adding New Features

When adding new features:

1. Determine which module the feature belongs to.
2. Create or modify the appropriate files.
3. Update the main application state in `models/app_state.rs` if needed.
4. Add UI components in the `ui` module.
5. Add any necessary API calls in the `api` module.
6. Ensure cross-platform compatibility with appropriate `#[cfg]` attributes.