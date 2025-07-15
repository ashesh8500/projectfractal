#!/usr/bin/env python3
"""
System integration test for Portfolio Optimizer Pro
"""
import sys
import time
import subprocess
import grpc
import portfolio_pb2
import portfolio_pb2_grpc
from portfolio_manager import PortfolioManager
from database import db_manager
from auth import auth_manager

def test_core_functionality():
    """Test core portfolio functionality."""
    print("🧪 Testing core portfolio functionality...")
    
    try:
        # Test portfolio manager
        pm = PortfolioManager({'AAPL': 100, 'GOOGL': 50})
        total_value = pm.get_current_value()
        print(f"✅ Portfolio created: ${total_value:.2f}")
        print(f"   Using mock data: {pm.is_using_mock_data}")
        
        # Test authentication
        user_info = auth_manager.authenticate('demo', 'demo123')
        if user_info:
            print(f"✅ Authentication successful: {user_info['username']}")
        else:
            print("❌ Authentication failed")
            return False
        
        # Test database operations
        user_id = user_info['user_id']
        db_manager.save_portfolio(user_id, 'test_portfolio', {'AAPL': 100, 'GOOGL': 50})
        portfolios = db_manager.list_portfolios(user_id)
        print(f"✅ Database operations successful: {len(portfolios)} portfolios")
        
        return True
        
    except Exception as e:
        print(f"❌ Core functionality test failed: {e}")
        return False

def test_grpc_server():
    """Test gRPC server functionality."""
    print("\n🌐 Testing gRPC server...")
    
    try:
        # Start server in background
        server_process = subprocess.Popen([
            sys.executable, 'server.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(3)
        
        # Test connection
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = portfolio_pb2_grpc.PortfolioServiceStub(channel)
            
            # Test authentication
            auth_request = portfolio_pb2.AuthRequest(username='demo', password='demo123')
            response = stub.Authenticate(auth_request)
            
            if response.success:
                print(f"✅ gRPC authentication successful: {response.user.username}")
                
                # Test creating a portfolio
                user_id = response.user.user_id
                create_request = portfolio_pb2.CreatePortfolioRequest(
                    user_id=user_id,
                    name='test_grpc_portfolio',
                    holdings=portfolio_pb2.Holdings(shares={'AAPL': 100, 'MSFT': 50})
                )
                portfolio_response = stub.CreatePortfolio(create_request)
                print(f"✅ gRPC portfolio created: {portfolio_response.name}")
                print(f"   Total value: ${portfolio_response.total_value:.2f}")
                print(f"   Using mock data: {portfolio_response.is_using_mock_data}")
                
                # Test listing portfolios
                list_request = portfolio_pb2.ListPortfoliosRequest(user_id=user_id)
                list_response = stub.ListPortfolios(list_request)
                print(f"✅ Portfolio listing: {len(list_response.portfolio_names)} portfolios")
                
                server_process.terminate()
                return True
            else:
                print(f"❌ gRPC authentication failed: {response.message}")
                server_process.terminate()
                return False
                
    except grpc.RpcError as e:
        print(f"❌ gRPC server test failed: {e}")
        if 'server_process' in locals():
            server_process.terminate()
        return False
    except Exception as e:
        print(f"❌ gRPC server test failed: {e}")
        if 'server_process' in locals():
            server_process.terminate()
        return False

def test_rust_frontend():
    """Test Rust frontend compilation."""
    print("\n🦀 Testing Rust frontend...")
    
    try:
        # Test compilation
        result = subprocess.run([
            'cargo', 'build', '--release'
        ], cwd='frontend_rust', capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Rust frontend compiled successfully")
            print("   Frontend binary ready at: frontend_rust/target/release/portfolio_frontend")
            return True
        else:
            print(f"❌ Rust frontend compilation failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Rust frontend test failed: {e}")
        return False

def main():
    """Run all system tests."""
    print("🚀 Portfolio Optimizer Pro - System Integration Test")
    print("=" * 60)
    
    results = []
    
    # Test core functionality
    results.append(test_core_functionality())
    
    # Test gRPC server
    results.append(test_grpc_server())
    
    # Test Rust frontend
    results.append(test_rust_frontend())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    tests = [
        "Core Functionality",
        "gRPC Server",
        "Rust Frontend"
    ]
    
    for i, (test_name, passed) in enumerate(zip(tests, results)):
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    all_passed = all(results)
    print(f"\n🎯 Overall Status: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 System is ready to use!")
        print("   1. Start server: python server.py")
        print("   2. Run frontend: cd frontend_rust && cargo run")
        print("   3. Login with demo/demo123")
    else:
        print("\n🔧 Please fix the failing tests before using the system.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())