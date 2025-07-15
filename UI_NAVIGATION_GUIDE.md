# Portfolio Optimizer Pro - UI Navigation Guide

## 🎯 How to Access Enhanced UI Features

### Step-by-Step Navigation

#### 1. **Start the System**
```bash
# Terminal 1 - Start the server
source /opt/homebrew/anaconda3/etc/profile.d/conda.sh
conda activate py313_base
cd "/Users/asheshkaji/Documents/University Files/Learning code/Stock Portfolio Project/portfolio_app"
python server.py

# Terminal 2 - Start the frontend
cd "/Users/asheshkaji/Documents/University Files/Learning code/Stock Portfolio Project/portfolio_app/frontend_rust"
cargo run --release
```

#### 2. **Create a Portfolio First**
Before you can see charts, you need to create a portfolio:

1. **In the Left Sidebar**, find the "➕ Create New Portfolio" section
2. **Add Holdings**:
   - Symbol: `AAPL` → Shares: `100` → Click "Add Holding"
   - Symbol: `GOOGL` → Shares: `50` → Click "Add Holding"
   - Symbol: `MSFT` → Shares: `75` → Click "Add Holding"
3. **Portfolio Name**: Enter a name like "My Portfolio"
4. **Click "🚀 Create Portfolio"**

#### 3. **Access Chart Features**
Once you have a portfolio, look for the "📊 Charts & Analysis" section in the sidebar:

**Chart Type Dropdown**:
- 📈 **Line Chart** - Traditional line graphs
- 📊 **Bar Chart** - Vertical bar visualization  
- 🕯️ **Candlestick** - (Currently shows placeholder, implementing full version below)

**Time Period Dropdown**:
- 1 Month, 3 Months, 6 Months, 1 Year, 2 Years, 5 Years

#### 4. **Generate Charts**
1. **Select your preferred chart type**
2. **Select time period**  
3. **Click "📈 Get Price History"**
4. **Charts will appear in the main panel**

#### 5. **Advanced Features**
- **🔧 Advanced Options**: Click to expand and enable "Show detailed metrics"
- **Data Source Indicators**: Look for ⚠️ warnings if mock data is being used
- **Portfolio Dashboard**: Shows weight distribution and strategy results

## 🐛 Common Issues & Solutions

### Issue 1: "No charts visible"
**Solution**: Make sure you've created a portfolio first and clicked "Get Price History"

### Issue 2: "Chart type doesn't change"
**Solution**: You need to click "Get Price History" again after changing chart type

### Issue 3: "Only seeing placeholder for candlestick"
**Solution**: I'm implementing the full candlestick chart below

## 📊 Current Feature Status

✅ **Working Features**:
- Line charts with multiple symbols
- Bar charts with price data
- Time period selection (1mo to 5y)
- Portfolio weight distribution charts
- Data source transparency indicators
- Real-time connection status

🚧 **In Development**:
- Full candlestick charts (implementing now)
- Advanced analytics
- Risk metrics
- Correlation matrix

## 🎨 UI Layout Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ 📊 Portfolio Optimizer Pro    🟢 Connected  ⚠️ Using Mock Data     │
├─────────────────┬───────────────────────────────────────────────────┤
│ 📂 Portfolio    │                                                   │
│ Management      │           📊 Portfolio Dashboard                  │
│                 │           ┌─────────────────────────────────────┐ │
│ ➕ Create New   │           │ Name: My Portfolio                  │ │
│ Portfolio       │           │ Total Value: $45,894.00            │ │
│                 │           │ ⚠️ Mock Data                        │ │
│ 🎯 Strategy     │           └─────────────────────────────────────┘ │
│                 │                                                   │
│ 📊 Charts &     │           📈 Current Weights                      │
│ Analysis        │           [Weight distribution bar chart]         │
│ ┌─────────────┐ │                                                   │
│ │Period: 1y   │ │           📈 Price History                        │
│ │Type: Line   │ │           [Price charts - Line/Bar/Candlestick]   │
│ └─────────────┘ │                                                   │
│                 │                                                   │
│ 🔧 Advanced     │                                                   │
│ Options         │                                                   │
└─────────────────┴───────────────────────────────────────────────────┘
```

The chart type selector and time period selector are in the left sidebar under "📊 Charts & Analysis". Make sure to create a portfolio first, then use these controls and click "Get Price History" to see the charts in the main panel.