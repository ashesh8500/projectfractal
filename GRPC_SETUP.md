# gRPC Server and Rust Frontend Setup Guide

This guide explains how to run the production-grade gRPC server with the Rust frontend.

## Architecture Overview

- **Python gRPC Server**: Handles portfolio management, strategy execution, and data fetching
- **Rust Frontend**: Modern UI built with egui for cross-platform desktop applications
- **Protocol Buffers**: Type-safe communication between client and server

## Prerequisites

1. **Python Environment**: 
   - Python 3.8+ (tested with conda py313_base environment)
   - Required packages: grpcio, grpcio-tools, and existing portfolio app dependencies

2. **Rust Environment**:
   - Rust 1.70+ with cargo
   - Required crates: egui, eframe, tonic, prost, tokio

## Setup Instructions

### 1. Install Python Dependencies

```bash
# Activate conda environment
source /opt/homebrew/anaconda3/etc/profile.d/conda.sh
conda activate py313_base

# Install gRPC dependencies
pip install grpcio grpcio-tools
```

### 2. Generate gRPC Code (Already Done)

```bash
# Generate Python protobuf code
python -m grpc_tools.protoc -Iproto --python_out=. --grpc_python_out=. proto/portfolio.proto
```

### 3. Build Rust Frontend

```bash
cd frontend_rust
cargo build --release
```

## Running the System

### Method 1: Full System (Server + Frontend)

**Terminal 1** - Start Python gRPC Server:
```bash
source /opt/homebrew/anaconda3/etc/profile.d/conda.sh
conda activate py313_base
cd "/Users/asheshkaji/Documents/University Files/Learning code/Stock Portfolio Project/portfolio_app"
python server.py
```

**Terminal 2** - Start Rust Frontend:
```bash
cd "/Users/asheshkaji/Documents/University Files/Learning code/Stock Portfolio Project/portfolio_app/frontend_rust"
cargo run --release
```

### Method 2: Mock Frontend Only

```bash
cd frontend_rust
cargo run
```

This runs the frontend in mock mode with sample data for UI demonstration.

## Testing

### Test Server Functionality
```bash
python test_server.py
```

### Test Rust Frontend Build
```bash
cd frontend_rust
cargo check
```

## Features

### Python gRPC Server
- **Portfolio Management**: Create, load, and manage portfolios
- **Strategy Execution**: Run Bollinger Bands, ML, and Momentum strategies
- **Price Data**: Fetch and serve historical price data
- **Error Handling**: Comprehensive error handling with proper gRPC status codes
- **Database**: SQLite persistence for portfolios and results

### Rust Frontend
- **Modern UI**: Built with egui for native desktop performance
- **Real-time Updates**: Async communication with gRPC server
- **Interactive Charts**: Price history visualization with egui_plot
- **Parameter Tuning**: Dynamic strategy parameter controls
- **Error Handling**: User-friendly error messages and status indicators

## gRPC Service Methods

### `CreatePortfolio`
- **Request**: Portfolio name and holdings (symbol -> shares)
- **Response**: Created portfolio with total value and weights

### `LoadPortfolio`
- **Request**: Portfolio name
- **Response**: Loaded portfolio data

### `RunStrategy`
- **Request**: Portfolio name, strategy name, and parameters
- **Response**: New weights and changes

### `GetPriceHistory`
- **Request**: Portfolio name and period
- **Response**: Historical price data for all symbols

## File Structure

```
portfolio_app/
├── proto/
│   └── portfolio.proto          # Protocol buffer definitions
├── frontend_rust/
│   ├── src/
│   │   └── main.rs             # Rust frontend application
│   ├── Cargo.toml              # Rust dependencies
│   └── build.rs                # Protobuf compilation
├── server.py                   # Python gRPC server
├── portfolio_pb2.py            # Generated protobuf messages
├── portfolio_pb2_grpc.py       # Generated gRPC service
└── test_server.py              # Server functionality tests
```

## Production Considerations

### Security
- Add authentication and authorization
- Use TLS for encrypted communication
- Implement rate limiting

### Scalability
- Add connection pooling
- Implement caching for frequently accessed data
- Consider load balancing for multiple server instances

### Monitoring
- Add logging and metrics
- Implement health checks
- Monitor gRPC service performance

## Troubleshooting

### Common Issues

1. **Server won't start**:
   - Check if port 50051 is already in use
   - Verify conda environment is activated
   - Ensure all dependencies are installed

2. **Frontend can't connect**:
   - Verify server is running on port 50051
   - Check firewall settings
   - Ensure gRPC server is accessible

3. **Build errors**:
   - Update Rust toolchain: `rustup update`
   - Clean and rebuild: `cargo clean && cargo build`

### Debug Mode

Enable debug logging in the server:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

1. **Enhanced Frontend**: Add full async gRPC communication
2. **Authentication**: Implement user authentication
3. **Deployment**: Container-based deployment with Docker
4. **Performance**: Add caching and optimization
5. **Features**: Additional portfolio analysis tools

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the server logs in `portfolio_app.log`
3. Test individual components using the test scripts