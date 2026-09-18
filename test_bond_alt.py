import requests
import json
from datetime import datetime, timedelta

def get_bond(ticker):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        
        # Zip and remove nulls
        valid_data = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
        if not valid_data:
            return None
            
        curr_price = valid_data[-1][1]
        
        now_ts = datetime.utcnow().timestamp()
        
        # 1 week ago
        w1_ts = now_ts - (7 * 86400)
        w1_data = [x for x in valid_data if x[0] >= w1_ts]
        w1_price = w1_data[0][1] if w1_data else curr_price
        
        # 1 month ago
        m1_ts = now_ts - (30 * 86400)
        m1_data = [x for x in valid_data if x[0] >= m1_ts]
        m1_price = m1_data[0][1] if m1_data else curr_price
        
        # 1 year ago
        y1_price = valid_data[0][1]
        
        return curr_price, w1_price, m1_price, y1_price
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

print(get_bond('IEF'))
print(get_bond('2515.T'))
