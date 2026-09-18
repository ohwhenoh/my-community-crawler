import yfinance as yf

# Test Exchange Rates
tickers = ["JPYKRW=X", "JPYUSD=X", "USDKRW=X"]
for t in tickers:
    tick = yf.Ticker(t)
    data = tick.history(period="1d")
    print(f"{t}: {data['Close'].iloc[-1] if not data.empty else 'No data'}")

# Test Bonds
bonds = ["ZN=F", "FLG=F", "2515.T", "^TNX", "^JN10", "^UK10G", "IEF", "IGLT.L", "2561.T"]
for b in bonds:
    tick = yf.Ticker(b)
    data = tick.history(period="1d")
    print(f"{b}: {data['Close'].iloc[-1] if not data.empty else 'No data'}")
