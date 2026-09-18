import yfinance as yf
import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
})

print("Testing FX download with session...")
try:
    fx_data = yf.download("JPYKRW=X", period="1d", progress=False, session=session)['Close']
    print(fx_data)
except Exception as e:
    print(e)

print("Testing Ticker with session...")
try:
    t = yf.Ticker("IEF", session=session)
    hist = t.history(period="1mo")
    print(hist)
except Exception as e:
    print(e)

