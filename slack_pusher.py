import os
import json
import requests
import base64

import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")

load_env()

def get_slack_webhook():
    env_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if env_url: return env_url
    fallback_b64 = "aHR0cHM6Ly9ob29rcy5zbGFjay5jb20vc2VydmljZXMvVDA5ODVFVlNKU1MvQjBDOFU1NFVLTlYvM0xqWEwxV2kyWE4wN1BOWHNxd3IyN0hq"
    try:
        return base64.b64decode(fallback_b64).decode("utf-8")
    except:
        return ""

SLACK_WEBHOOK_URL = get_slack_webhook()
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_history.json")
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yield_cache.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except: pass
    return set()

def save_history(history_set):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(history_set), f)
    except: pass

def get_te_yield(country_path):
    cache_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except: pass
        
    val = None
    
    eodhd_key = os.environ.get("EODHD_API_KEY")
    if eodhd_key:
        eodhd_map = {
            "united-states": "US10Y.GBOND",
            "south-korea": "KR10Y.GBOND",
            "china": "CN10Y.GBOND",
            "japan": "JP10Y.GBOND",
            "malaysia": "MY10Y.GBOND",
            "euro-area": "DE10Y.GBOND",
            "switzerland": "CH10Y.GBOND",
            "hong-kong": "HK10Y.GBOND",
            "indonesia": "ID10Y.GBOND",
            "turkey": "TR10Y.GBOND",
            "israel": "IL10Y.GBOND"
        }
        sym = eodhd_map.get(country_path)
        if sym:
            url = f"https://eodhd.com/api/real-time/{sym}?api_token={eodhd_key}&fmt=json"
            try:
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    close_val = data.get("close")
                    if close_val and close_val != "NA": val = float(close_val)
                    else:
                        prev = data.get("previousClose")
                        if prev and prev != "NA": val = float(prev)
            except: pass

    if val is None and country_path == "united-states" and os.environ.get("FRED_API_KEY"):
        api_key = os.environ.get("FRED_API_KEY")
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={api_key}&file_type=json&sort_order=desc&limit=1"
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if "observations" in data and len(data["observations"]) > 0:
                val = float(data["observations"][0]["value"])
        except: pass

    if val is None:
        cnbc_map = {
            "south-korea": "KR10Y-KR", "china": "CN10Y-CN", "japan": "JP10Y-JP",
            "euro-area": "DE10Y-DE", "united-states": "US10Y",
            "switzerland": "CH10Y-CH", "hong-kong": "HK10Y-HK", "indonesia": "ID10Y-ID", 
            "turkey": "TR10Y-TR", "israel": "IL10Y-IL"
        }
        symbol = cnbc_map.get(country_path)
        if symbol:
            headers = {'User-Agent': 'Mozilla/5.0'}
            url = f"https://www.cnbc.com/quotes/{symbol}"
            try:
                import re
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    m = re.search(r'QuoteStrip-lastPrice"[^>]*>([\d\.]+)', res.text)
                    if m: val = float(m.group(1))
            except: pass

    if val is not None:
        cache_data[country_path] = {"value": val, "date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")}
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except: pass
        return val, False
    else:
        if country_path in cache_data:
            return cache_data[country_path]["value"], cache_data[country_path]["date"]
        fallbacks = {
            "united-states": 5.23, "china": 1.70, "south-korea": 4.39,
            "japan": 3.02, "malaysia": 3.96, "euro-area": 4.09
        }
        return fallbacks.get(country_path, 0.0), "오래된 캐시"

def get_frankfurter_fx():
    base = "USD"
    symbols = ["CNY", "KRW", "JPY", "MYR", "EUR", "CHF", "HKD", "IDR", "TRY", "ILS"]
    try:
        now = datetime.now(timezone(timedelta(hours=9)))
        three_months_ago = now - timedelta(days=90)
        
        current_res = requests.get(f"https://api.frankfurter.app/latest?from={base}&to={','.join(symbols)}", timeout=10)
        current_data = current_res.json().get('rates', {})
        
        hist_date = three_months_ago.strftime("%Y-%m-%d")
        if three_months_ago.weekday() >= 5:
            hist_date = (three_months_ago - timedelta(days=three_months_ago.weekday() - 4)).strftime("%Y-%m-%d")
            
        hist_res = requests.get(f"https://api.frankfurter.app/{hist_date}?from={base}&to={','.join(symbols)}", timeout=10)
        hist_data = hist_res.json().get('rates', {})
        
        return current_data, hist_data
    except:
        return {}, {}

def get_b2b_sales_report():
    us_yield_data = get_te_yield("united-states")
    if not us_yield_data: return ""
    us_yield, us_cache_date = us_yield_data
    if us_yield == 0.0: return ""
        
    countries = [
        {"name": "중국", "sym": "CNY", "flag": "🇨🇳", "te_path": "china"},
        {"name": "한국", "sym": "KRW", "flag": "🇰🇷", "te_path": "south-korea"},
        {"name": "일본", "sym": "JPY", "flag": "🇯🇵", "te_path": "japan"},
        {"name": "말레이시아", "sym": "MYR", "flag": "🇲🇾", "te_path": "malaysia"},
        {"name": "유럽", "sym": "EUR", "flag": "🇪🇺", "te_path": "euro-area"},
        {"name": "스위스", "sym": "CHF", "flag": "🇨🇭", "te_path": "switzerland"},
        {"name": "홍콩", "sym": "HKD", "flag": "🇭🇰", "te_path": "hong-kong"},
        {"name": "인도네시아", "sym": "IDR", "flag": "🇮🇩", "te_path": "indonesia"},
        {"name": "터키", "sym": "TRY", "flag": "🇹🇷", "te_path": "turkey"},
        {"name": "이스라엘", "sym": "ILS", "flag": "🇮🇱", "te_path": "israel"}
    ]
    
    curr_fx, hist_fx = get_frankfurter_fx()
    if not curr_fx or not hist_fx: return ""

    has_cache = bool(us_cache_date)
    
    def get_index_change(symbol):
        try:
            res = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if res.status_code == 200:
                meta = res.json()['chart']['result'][0]['meta']
                return (meta['regularMarketPrice'] / meta['chartPreviousClose'] - 1) * 100
        except: pass
        return 0.0
        
    def get_vix():
        try:
            res = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/^VIX", headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if res.status_code == 200:
                return float(res.json()['chart']['result'][0]['meta']['regularMarketPrice'])
        except: pass
        return 0.0

    us_avg = (get_index_change('^IXIC') + get_index_change('^GSPC')) / 2
    cn_avg = (get_index_change('000001.SS') + get_index_change('^HSI')) / 2
    kr_idx = get_index_change('^KS11')
    sg_idx = get_index_change('^STI')
    my_idx = get_index_change('^KLSE')
    id_idx = get_index_change('^JKSE')
    tw_idx = get_index_change('^TWII')
    vix_val = get_vix()
    
    def gc(val): return "🟢" if val > 0 else "🔴"
    
    report = f"🔄 *[글로벌 B2B 매력도 분석]*\n기준: {datetime.now(timezone(timedelta(hours=9))).strftime('%y-%m-%d')} | 3개월 전 대비\n\n"
    report += f"📊 *글로벌 증시 전광판* (Top 기업 대용 지수)\n"
    
    us_status = f"{gc(us_avg)} {us_avg:+.2f}%"
    if vix_val >= 20.0 or us_yield >= 4.5:
        us_status = f"🔴 진입 금지 (VIX: {vix_val:.1f} / 10Y: {us_yield:.2f}%)"
        
    report += f"🇺🇸 미국 (나스닥/S&P500 평균): {us_status}\n" 
    report += f"🇨🇳 중국 (상해/항셍 평균): {gc(cn_avg)} {cn_avg:+.2f}%\n"
    report += f"🇰🇷 한국 (KOSPI): {gc(kr_idx)} {kr_idx:+.2f}%\n"
    report += f"🇸🇬 싱가포르 (STI): {gc(sg_idx)} {sg_idx:+.2f}%\n"
    report += f"🇲🇾 말레이시아 (KLCI): {gc(my_idx)} {my_idx:+.2f}%\n"
    report += f"🇮🇩 인도네시아 (IDX): {gc(id_idx)} {id_idx:+.2f}%\n"
    report += f"🇹🇼 대만 (TAIEX): {gc(tw_idx)} {tw_idx:+.2f}%\n"
    report += f"_(참고: 🟢 초록=상승/좋음, 🔴 빨강=하락/나쁨 - 서양식 기준)_\n\n"
    
    for c in countries:
        local_yield_data = get_te_yield(c["te_path"])
        local_yield, local_cache_date = local_yield_data if local_yield_data else (0.0, False)
        if local_cache_date: has_cache = True
        
        sym = c["sym"]
        cfx = curr_fx.get(sym, 0)
        hfx = hist_fx.get(sym, 0)
        
        if cfx == 0 or hfx == 0: continue
        
        # 금리 데이터가 없는 국가는 제외 (노이즈 방지)
        if local_yield == 0.0 or local_yield is None:
            continue
            
        spread = us_yield - local_yield
        raw_fx_change = (cfx / hfx - 1.0) * 100.0
        trend_word = "상승" if raw_fx_change > 0 else "하락"
        
        if raw_fx_change <= -1.0: fx_gain_score = abs(raw_fx_change)
        elif raw_fx_change >= 1.0: fx_gain_score = -abs(raw_fx_change)
        else: fx_gain_score = -raw_fx_change
            
        final_score = fx_gain_score + (spread * -1.0)
        if final_score >= 0.5: status = "🔥 엑셀 (황금타이밍)"
        elif final_score < -0.3: status = "🛑 브레이크 (진입금지)"
        else: status = "⏸️ 대기 (기어중립)"
            
        cache_warn = f" (⚠️캐시)" if local_cache_date else ""
        
        # 갤럭시 S22 울트라 화면에 맞춘 모바일 UI 최적화
        report += f"\n{c['flag']} *{c['name']} ({sym})*{cache_warn}\n"
        report += f" • 환율: {cfx:,.4f} ({trend_word} {abs(raw_fx_change):.2f}%)\n"
        report += f" • 금리: 🇺🇸{us_yield:.2f}% vs {c['flag']}{local_yield:.2f}%\n"
        report += f" • 판정: {status} [{final_score:+.2f}%]\n"
        
    if has_cache:
        report = report.replace("🔄 *[글로벌 B2B 매력도 분석]*", "🔄 *[글로벌 B2B 매력도 분석]*\n🚨 *[주의: API 통신 장애로 일부 국가의 경우 최근 캐시 데이터가 반영되었습니다]*")
        
    return report.strip()


TARGET_KEYWORDS = [
    "빅테크", "실적", "어닝", "가이던스", "earnings", "revenue", "guidance", "big tech", "apple", "microsoft", "google", "meta", "amazon", "nvidia", "tesla",
    "ai", "인프라", "데이터센터", "gpu", "tpu", "hbm", "인공지능", "artificial intelligence", "data center", "infrastructure",
    "보안", "해킹", "랜섬웨어", "취약점", "유출", "cyber", "security", "hack", "breach", "ransomware", "vulnerability",
    "지정학", "매크로", "geopolitical", "macro",
    "중국 증시", "상해", "홍콩 증시", "항셍", "china market", "shanghai", "hang seng", "chinese stock",
    "금리", "fed", "fomc", "기준금리", "rate", "interest", "rate cut", "rate hike",
    "환율", "달러", "원화", "엔화", "위안화", "exchange rate", "currency", "usd", "krw", "jpy", "cny",
    "법안", "거부권", "필리버스터", "의회", "상원", "하원", "bill", "veto", "filibuster", "senate", "house of representatives", "congress",
    "이란", "전쟁", "우크라이나", "러시아", "이스라엘", "중동", "iran", "war", "ukraine", "russia", "israel", "middle east", "conflict",
    "드론", "휴머노이드", "로봇", "유니트리", "drone", "humanoid", "robot", "unitree",
    "선거", "자금", "기부", "election fund", "donation", "campaign", "pac",
    "암호화폐", "비트코인", "이더리움", "crypto", "bitcoin", "ethereum", "btc", "eth",
    "레딧", "reddit", "rddt",
    "백질이영양증", "leukodystrophy", "aadc", "hemophilia", "혈우병", "치료제", "신약", "fda",
    "이우환", "lee ufan", "워블리라이프", "wobbly life", "로블록스", "roblox", "fortnite", "포트나이트",
    "개방형 팬", "open ran", "hbf", "예가체프", "게이샤", "yirgacheffe", "geisha", "샤오미", "xiaomi", 
    "부동산", "real estate", "농지", "투기", "farmland", "speculation", 
    "지지율", "approval rating", "조희대", "신천지", "shincheonji", 
    "국내 증시", "코스피", "코스닥", "kospi", "kosdaq", 
    "사법부", "judiciary", "네타냐후", "netanyahu", "ai 기본 사회", "ai society"
]

import re

def filter_trends_by_keywords(trends_list):
    filtered = []
    for t in trends_list:
        text_to_search = (t["keyword"] + " " + " ".join([n["title"] for n in t.get("news", [])])).lower()
        
        # 비영어/비한국어 꼼수 필터링
        if re.search(r'[À-ÿœæøåß]', text_to_search):
            continue
        foreign_stop = [r'\bhet\b', r'\been\b', r'\bbij\b', r'\bund\b', r'\boder\b', r'\bel\b', r'\bla\b', r'\blos\b', r'\blas\b', r'\bpara\b', r'\bcryptobeurs\b']
        is_foreign = False
        for fw in foreign_stop:
            if re.search(fw, text_to_search):
                is_foreign = True
                break
        if is_foreign: continue

        matched = False
        for k in TARGET_KEYWORDS:
            k_lower = k.lower()
            if re.search(r'[a-z]', k_lower):
                # 영문 키워드는 단어 단위 매칭 (word boundary)
                if re.search(rf'\b{re.escape(k_lower)}\b', text_to_search):
                    matched = True
                    break
            else:
                # 한글 키워드는 부분 일치 허용
                if k_lower in text_to_search:
                    matched = True
                    break
        if matched:
            filtered.append(t)
    return filtered

def summarize_all_trends(all_trends_info):
    # LLM removed as per user instruction. Fast fallback to news titles.
    for t in all_trends_info:
        t["summary"] = t["news"][0]["title"] if t["news"] else "관련 뉴스 없음"
    return all_trends_info

def get_google_trends_raw(geo="KR", limit=5):
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return []
        root = ET.fromstring(res.text)
        channel = root.find("channel")
        items = channel.findall("item")[:limit]
        ns = {"ht": "https://trends.google.com/trending/rss"}
        
        trends_info = []
        for item in items:
            title = item.find("title").text if item.find("title") is not None else ""
            traffic = item.find("ht:approx_traffic", ns)
            traffic_str = traffic.text.replace("+", "") if traffic is not None else ""
            
            import urllib.parse
            link = f"https://www.google.com/search?q={urllib.parse.quote(title)}" if title else ""
            
            news_items = item.findall("ht:news_item", ns)
            news_list = []
            for n_item in news_items:
                n_title = n_item.find("ht:news_item_title", ns).text if n_item.find("ht:news_item_title", ns) is not None else ""
                n_url = n_item.find("ht:news_item_url", ns).text if n_item.find("ht:news_item_url", ns) is not None else ""
                if n_title: news_list.append({"title": n_title, "url": n_url})
            
            trends_info.append({
                "keyword": title,
                "traffic": traffic_str,
                "search_link": link,
                "news": news_list
            })
            
        return trends_info
    except Exception as e:
        print(f"Google Trends error ({geo}):", e)
        return []

def send_slack():
    SENT_URLS = load_history()
    NEW_SENT_URLS = set()

    # 1. B2B 매력도 분석
    print("Generating B2B Report...")
    b2b_report = get_b2b_sales_report()
    payload_b2b = None
    if b2b_report:
        payload_b2b = {
            "text": "F5 B2B 매력도 분석",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🎯 F5 B2B 분석 (발행: {datetime.now(timezone(timedelta(hours=9))).strftime('%m/%d %H:%M')})"
                    }
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": b2b_report}
                }
            ]
        }

    # 2. 글로벌 구글 트렌드
    print("Collecting Google Trends...")
    geos = {
        "South Korea": "KR", "Singapore": "SG", "Netherlands": "NL",
        "Hong Kong": "HK", "Switzerland": "CH", "Israel": "IL",
        "Japan": "JP", "California (US)": "US-CA"
    }
    
    all_trends = []
    for name, code in geos.items():
        res = get_google_trends_raw(code, 20)
        if res:
            for r in res: r['geo_name'] = name
            all_trends.extend(res)

    
    all_trends = filter_trends_by_keywords(all_trends)
    summarized_all = summarize_all_trends(all_trends)

    
    # S22 Ultra에 맞게 글로벌 경제 / 라이프 헬스로 카테고리화
    trends_by_category = {"글로벌 경제": [], "라이프/헬스": []}
    
    geo_short = {
        "South Korea": "KR", "Singapore": "SG", "Netherlands": "NL",
        "Hong Kong": "HK", "Switzerland": "CH", "Israel": "IL",
        "Japan": "JP", "California (US)": "US"
    }

    for t in summarized_all:
        cat = t.get('category', '글로벌 경제')
        g = geo_short.get(t['geo_name'], t['geo_name'])
        kw = t["keyword"]
        s_link = t["search_link"]
        summary = t["summary"]
        top_news_url = t["news"][0]["url"] if t["news"] else s_link
        
        # S22 모바일 화면 최적화: [국가] 키워드링크: 요약링크
        trends_by_category[cat].append(f"• [{g}] <{s_link}|*{kw}*>: <{top_news_url}|{summary}>")

    trends_blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🌐 글로벌 이슈 트래킹"}
        }
    ]
    
    for cat_name in ["글로벌 경제", "라이프/헬스"]:
        if trends_by_category[cat_name]:
            items = trends_by_category[cat_name]
            chunk_size = 10  # 3000자 제한 방지
            for i in range(0, len(items), chunk_size):
                chunk = items[i:i + chunk_size]
                header_text = f"*{cat_name}*" if i == 0 else f"*{cat_name}* (계속)"
                trends_blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": header_text + "\n" + "\n".join(chunk)}
                })

    from collections import Counter
    stopwords = set([
        "the", "in", "of", "and", "to", "a", "is", "for", "on", "with", "from", "at", "by", "this", "that", "it", "are", "be", "an", "as", "vs", "vs.",
        "은", "는", "이", "가", "을", "를", "에", "에서", "의", "로", "으로", "과", "와", "도", "다", "들", "수", "할", "위해", "대한", "및",
        "이슈", "요약", "불가"
    ])
    words = []
    for t in summarized_all:
        text = t["keyword"] + " " + t.get("summary", "")
        if t["news"]: text += " " + t["news"][0]["title"]
        clean_text = re.sub(r'[^\w\s\uac00-\ud7a3]', ' ', text)
        for w in clean_text.lower().split():
            if len(w) > 1 and w not in stopwords and not w.isdigit():
                words.append(w)
    
    top10 = Counter(words).most_common(10)
    if top10:
        top_str = " | ".join([f"*{w}*({c})" for w, c in top10])
        trends_blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"🔥 *오늘의 핵심 키워드 Top 10*: {top_str}"}]
        })

    payload_trends = {"text": "글로벌 트렌드 분석", "blocks": trends_blocks}
    
    # [E2E 텍스트 풀-프린트 검증]
    print("--- PAYLOAD 1: B2B ---")
    print(json.dumps(payload_b2b, ensure_ascii=False, indent=2))
    print("--- PAYLOAD 2: TRENDS ---")
    print(json.dumps(payload_trends, ensure_ascii=False, indent=2))
    print("------------------------")
    
    if SLACK_WEBHOOK_URL:
        try:
            if payload_b2b:
                res1 = requests.post(SLACK_WEBHOOK_URL, json=payload_b2b, timeout=10)
                print("B2B 전송:", res1.status_code)
            res2 = requests.post(SLACK_WEBHOOK_URL, json=payload_trends, timeout=10)
            print("Trends 전송:", res2.status_code)
            
            for t in summarized_all:
                if t["news"]: NEW_SENT_URLS.add(t["news"][0]["url"])
            SENT_URLS.update(NEW_SENT_URLS)
            save_history(SENT_URLS)
        except Exception as e:
            print("Slack 발송 에러:", e)

if __name__ == "__main__":
    send_slack()