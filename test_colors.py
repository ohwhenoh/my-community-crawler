import requests

def get_yahoo_full(ticker):
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
    r = requests.get(url, headers=headers, timeout=5)
    meta = r.json()['chart']['result'][0]['meta']
    return float(meta['regularMarketPrice']), float(meta['chartPreviousClose'])

usd_jpy, usd_jpy_p = get_yahoo_full('USDJPY=X')
usd_krw, usd_krw_p = get_yahoo_full('USDKRW=X')
usd_sgd, usd_sgd_p = get_yahoo_full('USDSGD=X')
usd_cny, usd_cny_p = get_yahoo_full('USDCNY=X')
usd_myr, usd_myr_p = get_yahoo_full('USDMYR=X')
eur_usd, eur_usd_p = get_yahoo_full('EURUSD=X')
eur_cny, eur_cny_p = get_yahoo_full('EURCNY=X')
eur_jpy, eur_jpy_p = get_yahoo_full('EURJPY=X')

def get_cross(c1, c2): return c1 / c2

jpy_krw, jpy_krw_p = get_cross(usd_krw, usd_jpy), get_cross(usd_krw_p, usd_jpy_p)
jpy_sgd, jpy_sgd_p = get_cross(usd_sgd, usd_jpy), get_cross(usd_sgd_p, usd_jpy_p)
jpy_usd, jpy_usd_p = get_cross(1, usd_jpy), get_cross(1, usd_jpy_p)
jpy_cny, jpy_cny_p = get_cross(usd_cny, usd_jpy), get_cross(usd_cny_p, usd_jpy_p)
krw_sgd, krw_sgd_p = get_cross(usd_sgd, usd_krw), get_cross(usd_sgd_p, usd_krw_p)
krw_usd, krw_usd_p = get_cross(1, usd_krw), get_cross(1, usd_krw_p)
krw_cny, krw_cny_p = get_cross(usd_cny, usd_krw), get_cross(usd_cny_p, usd_krw_p)
sgd_myr, sgd_myr_p = get_cross(usd_myr, usd_sgd), get_cross(usd_myr_p, usd_sgd_p)
sgd_krw, sgd_krw_p = get_cross(usd_krw, usd_sgd), get_cross(usd_krw_p, usd_sgd_p)
sgd_usd, sgd_usd_p = get_cross(1, usd_sgd), get_cross(1, usd_sgd_p)

def fmt(amount, rate, rate_p, currency, decimals):
    val = amount * rate
    val_p = amount * rate_p
    diff_pct = (val - val_p) / val_p * 100
    
    base_str = f"{val:,.{decimals}f} {currency}"
    
    if currency == 'MYR' and amount == 100 and val >= 349.0:
        base_str = f"🔥 {base_str} (좋은 가격입니다!)"
    elif currency == 'KRW' and amount == 10000 and val >= 87760.0:
        base_str = f"🔥 {base_str} (좋은 가격입니다!)"
    elif currency == 'SGD' and amount == 10000 and val >= 81.9:
        base_str = f"🔥 {base_str} (좋은 가격입니다!)"
    elif currency == 'KRW' and amount == 100 and val >= 139000.0:
        base_str = f"🔥 {base_str} (추천: 강달러 호기!)"
    elif currency == 'USD' and amount == 100 and val >= 112.0:
        base_str = f"🔥 {base_str} (추천: 강유로 호기!)"
    elif currency == 'USD' and amount == 100000 and val >= 75.0:
        base_str = f"🔥 {base_str} (추천: 원화강세 호기!)"
        
    if diff_pct >= 1.35:
        return f"🔴 *{base_str} ({diff_pct:+.2f}%)*"
    elif diff_pct >= 0.94:
        return f"🟡 *{base_str} ({diff_pct:+.2f}%)*"
    else:
        return f"🟢 *{base_str} ({diff_pct:+.2f}%)*"

print(f"• *100 SGD* = {fmt(100, sgd_myr, sgd_myr_p, 'MYR', 1)} | {fmt(100, sgd_krw, sgd_krw_p, 'KRW', 0)} | {fmt(100, sgd_usd, sgd_usd_p, 'USD', 1)}")
print(f"• *10,000 JPY* = {fmt(10000, jpy_krw, jpy_krw_p, 'KRW', 0)} | {fmt(10000, jpy_sgd, jpy_sgd_p, 'SGD', 1)} | {fmt(10000, jpy_usd, jpy_usd_p, 'USD', 1)} | {fmt(10000, jpy_cny, jpy_cny_p, 'CNY', 1)}")
print(f"• *100 USD* = {fmt(100, usd_krw, usd_krw_p, 'KRW', 0)} | {fmt(100, usd_sgd, usd_sgd_p, 'SGD', 1)} | {fmt(100, usd_cny, usd_cny_p, 'CNY', 1)}")
print(f"• *100 EUR* = {fmt(100, eur_usd, eur_usd_p, 'USD', 1)} | {fmt(100, eur_cny, eur_cny_p, 'CNY', 1)} | {fmt(100, eur_jpy, eur_jpy_p, 'JPY', 1)}")
print(f"• *100,000 KRW* = {fmt(100000, krw_sgd, krw_sgd_p, 'SGD', 1)} | {fmt(100000, krw_usd, krw_usd_p, 'USD', 1)} | {fmt(100000, krw_cny, krw_cny_p, 'CNY', 1)}")
