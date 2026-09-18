import re

with open('crawler_slack.py', 'r', encoding='utf-8') as f:
    content = f.read()

correct_macro_code = """
def get_macro_economic_data():
    try:
        # 환율 데이터 수집 (안정적인 무료 API 사용)
        fx_text = "💱 *[환율 방향 (Purchase Power Influence)]*\\n"
        try:
            r_usd = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10).json()['rates']
            usd_krw, usd_sgd, usd_cny, usd_jpy = r_usd['KRW'], r_usd['SGD'], r_usd['CNY'], r_usd['JPY']
            
            jpy_krw, jpy_sgd, jpy_usd, jpy_cny = usd_krw/usd_jpy, usd_sgd/usd_jpy, 1/usd_jpy, usd_cny/usd_jpy
            krw_sgd, krw_usd, krw_cny = usd_sgd/usd_krw, 1/usd_krw, usd_cny/usd_krw
            
            fx_text += f"• *10,000 JPY* = {jpy_krw*10000:,.0f} KRW | {jpy_sgd*10000:,.1f} SGD | {jpy_usd*10000:,.1f} USD | {jpy_cny*10000:,.1f} CNY\\n"
            fx_text += f"• *100,000 KRW* = {krw_sgd*100000:,.1f} SGD | {krw_usd*100000:,.1f} USD | {krw_cny*100000:,.1f} CNY\\n"
            fx_text += f"• *100 USD* = {usd_krw*100:,.0f} KRW | {usd_sgd*100:,.1f} SGD | {usd_cny*100:,.1f} CNY\\n\\n"
        except Exception as e:
            print(f"환율 수집 에러: {e}")
            fx_text += "⚠️ 환율 정보를 가져오지 못했습니다.\\n\\n"
            
        # 금리(국채 가격) 데이터 수집 (Yahoo 직접 호출)
        bond_text = "📉 *[금리 방향 (국채 가격 기반)]*\\n"
        bonds = {'미국': 'IEF', '일본': '2515.T', '영국': 'IGLT.L'}
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        for country, ticker in bonds.items():
            try:
                url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
                r = requests.get(url, headers=headers, timeout=10)
                data = r.json()
                result = data['chart']['result'][0]
                timestamps = result['timestamp']
                closes = result['indicators']['quote'][0]['close']
                
                valid_data = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
                if not valid_data: continue
                    
                curr_price = valid_data[-1][1]
                now_ts = datetime.utcnow().timestamp()
                
                w1_ts = now_ts - (7 * 86400)
                w1_data = [x for x in valid_data if x[0] >= w1_ts]
                w1_price = w1_data[0][1] if w1_data else curr_price
                
                m1_ts = now_ts - (30 * 86400)
                m1_data = [x for x in valid_data if x[0] >= m1_ts]
                m1_price = m1_data[0][1] if m1_data else curr_price
                
                y1_price = valid_data[0][1]
                
                direction = "하락 📉" if curr_price > m1_price else "상승 📈"
                bond_text += f"• *{country} 금리 {direction} 중* (근거: 10년물 국채ETF 가격 | 현재: {curr_price:,.2f} / 1주전: {w1_price:,.2f} / 1개월전: {m1_price:,.2f} / 1년전: {y1_price:,.2f})\\n"
            except Exception as e:
                print(f"Failed to fetch bond data for {country} ({ticker}): {e}")
                continue
                
        return fx_text + "\\n" + bond_text + "\\n"
    except Exception as e:
        print(f"거시경제 데이터 수집 실패: {e}")
        return "⚠️ 거시경제 지표 실시간 수집 지연\\n\\n"
"""

# Find the start and end of get_macro_economic_data
start_idx = content.find('def get_macro_economic_data():')
end_idx = content.find('def generate_korean_outreach_report():')

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + correct_macro_code + "\n" + content[end_idx:]
    with open('crawler_slack.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed macro function")
else:
    print("Could not find function bounds")
