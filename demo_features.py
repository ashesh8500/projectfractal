#!/usr/bin/env python3
"""
Demo script to showcase Portfolio Optimizer Pro features
"""
import grpc
import portfolio_pb2
import portfolio_pb2_grpc
import time

def demo_all_features():
    """Demonstrate all features of the portfolio system."""
    print("🎯 Portfolio Optimizer Pro - Feature Demo")
    print("=" * 50)
    
    try:
        # Connect to server
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = portfolio_pb2_grpc.PortfolioServiceStub(channel)
            
            # 1. Authentication
            print("🔐 1. Authentication Test")
            auth_request = portfolio_pb2.AuthRequest(username='demo', password='demo123')
            auth_response = stub.Authenticate(auth_request)
            
            if not auth_response.success:
                print("❌ Authentication failed!")
                return
            
            user_id = auth_response.user.user_id
            print(f"✅ Logged in as: {auth_response.user.username}")
            print(f"   User ID: {user_id}")
            print()
            
            # 2. Create Multiple Demo Portfolios
            print("📊 2. Creating Demo Portfolios")
            
            portfolios = [
                {
                    'name': 'Tech Growth Portfolio',
                    'holdings': {'AAPL': 100, 'GOOGL': 50, 'MSFT': 75, 'NVDA': 25}
                },
                {
                    'name': 'Conservative Portfolio', 
                    'holdings': {'SPY': 200, 'BND': 300, 'VTI': 150}
                },
                {
                    'name': 'Dividend Portfolio',
                    'holdings': {'JNJ': 80, 'PG': 60, 'KO': 120, 'PFE': 90}
                }
            ]
            
            for portfolio in portfolios:
                create_request = portfolio_pb2.CreatePortfolioRequest(
                    user_id=user_id,
                    name=portfolio['name'],
                    holdings=portfolio_pb2.Holdings(shares=portfolio['holdings'])
                )
                
                response = stub.CreatePortfolio(create_request)
                print(f"✅ Created: {response.name}")
                print(f"   Total Value: ${response.total_value:.2f}")
                print(f"   Mock Data: {response.is_using_mock_data}")
                print()
            
            # 3. List All Portfolios
            print("📋 3. Portfolio Listing")
            list_request = portfolio_pb2.ListPortfoliosRequest(user_id=user_id)
            list_response = stub.ListPortfolios(list_request)
            
            print(f"✅ Found {len(list_response.portfolio_names)} portfolios:")
            for name in list_response.portfolio_names:
                print(f"   • {name}")
            print()
            
            # 4. Test Different Strategies
            print("🎯 4. Strategy Testing")
            strategies = ['bollinger', 'ml', 'momentum']
            
            for strategy in strategies:
                print(f"   Testing {strategy} strategy...")
                strategy_request = portfolio_pb2.RunStrategyRequest(
                    user_id=user_id,
                    portfolio_name='Tech Growth Portfolio',
                    strategy_name=strategy,
                    params=portfolio_pb2.StrategyParams(params={})
                )
                
                try:
                    strategy_response = stub.RunStrategy(strategy_request)
                    print(f"   ✅ {strategy}: Success (Mock: {strategy_response.is_using_mock_data})")
                    
                    # Show top 2 weight changes
                    changes = list(strategy_response.changes.items())[:2]
                    for symbol, change in changes:
                        print(f"      {symbol}: {change*100:+.1f}%")
                        
                except Exception as e:
                    print(f"   ❌ {strategy}: {str(e)[:50]}...")
            print()
            
            # 5. Price History for Different Periods
            print("📈 5. Price History Testing")
            periods = ['1mo', '3mo', '1y']
            
            for period in periods:
                print(f"   Getting {period} price history...")
                history_request = portfolio_pb2.GetPriceHistoryRequest(
                    user_id=user_id,
                    portfolio_name='Tech Growth Portfolio',
                    period=period
                )
                
                try:
                    history_response = stub.GetPriceHistory(history_request)
                    symbols = len(history_response.symbols)
                    data_points = len(history_response.prices)
                    print(f"   ✅ {period}: {symbols} symbols, {data_points} data points (Mock: {history_response.is_using_mock_data})")
                    
                except Exception as e:
                    print(f"   ❌ {period}: {str(e)[:50]}...")
            print()
            
            # 6. Demo Instructions
            print("🎨 6. Frontend Demo Instructions")
            print("Now start the frontend to see all these features in action:")
            print()
            print("📋 Step-by-Step UI Demo:")
            print("1. Start frontend: cd frontend_rust && cargo run --release")
            print("2. You'll see 3 demo portfolios already created")
            print("3. Select 'Tech Growth Portfolio' from the name field")
            print("4. Click '🔄 Load Portfolio' to see the dashboard")
            print("5. In 'Charts & Analysis' section:")
            print("   • Try different periods: 1mo, 3mo, 1y")
            print("   • Switch chart types: Line → Bar → Candlestick")
            print("   • Click '📈 Get Price History' after each change")
            print("6. In 'Strategy' section:")
            print("   • Try different strategies: Bollinger, ML, Momentum")
            print("   • Click '🎯 Run Strategy' to see rebalancing")
            print("7. Enable '🔧 Advanced Options' → 'Show detailed metrics'")
            print()
            print("🎯 Chart Types Available:")
            print("• 📈 Line Chart - Traditional price lines")
            print("• 📊 Bar Chart - Vertical price bars") 
            print("• 🕯️ Candlestick - OHLC visualization with wicks")
            print()
            print("🔍 Look For:")
            print("• ⚠️ Data source warnings (real vs mock data)")
            print("• 🟢 Connection status in top bar")
            print("• Weight distribution bar charts")
            print("• Strategy change indicators (+/- percentages)")
            print()
            
    except grpc.RpcError as e:
        print(f"❌ Server Error: {e}")
        print("Make sure the server is running: python server.py")
        
    except Exception as e:
        print(f"❌ Demo Error: {e}")

def main():
    """Run the feature demo."""
    print("Starting Portfolio Optimizer Pro feature demonstration...")
    print("Make sure the server is running first!")
    print()
    
    try:
        demo_all_features()
        print("=" * 50)
        print("🎉 Demo completed! Start the frontend to explore the UI.")
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")

if __name__ == "__main__":
    main()