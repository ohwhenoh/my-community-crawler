import requests
from datetime import datetime, timedelta
import json

def get_fx():
    try:
        # USD base
        r_usd = requests.get('https://open.er-api.com/v6/latest/USD').json()['rates']
        usd_krw = r_usd['KRW']
        usd_sgd = r_usd['SGD']
        usd_cny = r_usd['CNY']
        usd_jpy = r_usd['JPY']
        
        # Cross rates
        jpy_krw = usd_krw / usd_jpy
        jpy_sgd = usd_sgd / usd_jpy
        jpy_usd = 1 / usd_jpy
        jpy_cny = usd_cny / usd_jpy
        
        krw_sgd = usd_sgd / usd_krw
        krw_usd = 1 / usd_krw
        krw_cny = usd_cny / usd_krw
        
        fx_text = "💱 *[환율 방향 (Purchase Power Influence)]*\n"
        fx_text += f"• *10,000 JPY* = {jpy_krw*10000:,.0f} KRW | {jpy_sgd*10000:,.1f} SGD | {jpy_usd*10000:,.1f} USD | {jpy_cny*10000:,.1f} CNY\n"
        fx_text += f"• *100,000 KRW* = {krw_sgd*100000:,.1f} SGD | {krw_usd*100000:,.1f} USD | {krw_cny*100000:,.1f} CNY\n"
        fx_text += f"• *100 USD* = {usd_krw*100:,.0f} KRW | {usd_sgd*100:,.1f} SGD | {usd_cny*100:,.1f} CNY\n"
        print(fx_text)
    except Exception as e:
        print("FX Error:", e)

get_fx()
