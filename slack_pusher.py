import os
import json
import time
import requests

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
    # 보안: 웹훅 주소는 환경 변수에서만 읽는다. 코드 안에 대체값을 두지 않는다.
    # 슬랙에서 기존 웹훅을 폐기하고 새 주소를 발급한 뒤, .env 파일에 SLACK_WEBHOOK_URL로 넣는다.
    return os.environ.get("SLACK_WEBHOOK_URL", "").strip()

SLACK_WEBHOOK_URL = get_slack_webhook()
HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HISTORY_FILE = os.path.join(HISTORY_DIR, "sent_history.json")
CACHE_FILE = os.path.join(HISTORY_DIR, "yield_cache.json")
os.makedirs(HISTORY_DIR, exist_ok=True)

# 출처 추적: get_te_yield()가 마지막으로 쓴 출처/날짜를 나라별로 기록한다.
# (값, 캐시날짜) 반환 형태를 바꾸지 않기 위해 별도 사전에 둔다.
YIELD_SOURCE = {}
FX_META = {"fx_date": "", "hist_date": ""}

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
                    if close_val and close_val != "NA":
                        val = float(close_val)
                        YIELD_SOURCE[country_path] = ("EODHD 실시간", datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"))
                    else:
                        prev = data.get("previousClose")
                        if prev and prev != "NA":
                            val = float(prev)
                            YIELD_SOURCE[country_path] = ("EODHD 실시간", datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"))
            except: pass

    if val is None and country_path == "united-states" and os.environ.get("FRED_API_KEY"):
        api_key = os.environ.get("FRED_API_KEY")
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={api_key}&file_type=json&sort_order=desc&limit=1"
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if "observations" in data and len(data["observations"]) > 0:
                val = float(data["observations"][0]["value"])
                YIELD_SOURCE[country_path] = ("FRED 일간", str(data["observations"][0].get("date", "")))
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
                    if m:
                        val = float(m.group(1))
                        YIELD_SOURCE[country_path] = ("CNBC 현재값", datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"))
            except: pass

    if val is not None:
        if country_path not in YIELD_SOURCE:
            YIELD_SOURCE[country_path] = ("실시간", datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d"))
        cache_data[country_path] = {"value": val, "date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")}
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except: pass
        return val, False
    else:
        if country_path in cache_data:
            # 8일 넘게 묵은 캐시는 쓰지 않는다. 낡은 값이 조용히 들어가는 것을 막는다.
            try:
                cached_date = datetime.strptime(str(cache_data[country_path]["date"])[:10], "%Y-%m-%d").date()
                age_days = (datetime.now(timezone(timedelta(hours=9))).date() - cached_date).days
            except Exception:
                age_days = 999
            if age_days <= 8:
                YIELD_SOURCE[country_path] = ("캐시", str(cache_data[country_path]["date"]))
                return cache_data[country_path]["value"], cache_data[country_path]["date"]
        # 낡은 기본값은 쓰지 않는다. 출처가 실패하면 자료 없음으로 표시한다.
        YIELD_SOURCE[country_path] = ("자료 없음", "")
        return 0.0, "자료 없음"

def get_frankfurter_fx():
    base = "USD"
    symbols = ["CNY", "KRW", "JPY", "MYR", "EUR", "CHF", "HKD", "IDR", "TRY", "ILS"]
    try:
        now = datetime.now(timezone(timedelta(hours=9)))
        three_months_ago = now - timedelta(days=90)
        
        current_res = requests.get(f"https://api.frankfurter.dev/v1/latest?from={base}&to={','.join(symbols)}", timeout=10)
        _cur_json = current_res.json()
        current_data = _cur_json.get('rates', {})
        FX_META["fx_date"] = str(_cur_json.get('date', ''))
        
        hist_date = three_months_ago.strftime("%Y-%m-%d")
        if three_months_ago.weekday() >= 5:
            hist_date = (three_months_ago - timedelta(days=three_months_ago.weekday() - 4)).strftime("%Y-%m-%d")
            
        hist_res = requests.get(f"https://api.frankfurter.dev/v1/{hist_date}?from={base}&to={','.join(symbols)}", timeout=10)
        hist_data = hist_res.json().get('rates', {})
        FX_META["hist_date"] = hist_date
        
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
    
    _fx_date = FX_META.get("fx_date") or "날짜 미상"
    report = f"🔄 *[글로벌 B2B 매력도 분석]*\n기준: {datetime.now(timezone(timedelta(hours=9))).strftime('%y-%m-%d')} | 환율 3개월 전 대비 (유럽중앙은행 고시 {_fx_date}) | 판정은 자체 규칙, 투자 신호 아님\n\n"
    report += f"📊 *글로벌 증시 전광판* (Top 기업 대용 지수)\n"
    _us_src = YIELD_SOURCE.get("united-states", ("자료 없음", ""))
    report += f"미국 10년 금리: {us_yield:.2f}% ({_us_src[0]}{' ' + _us_src[1] if _us_src[1] else ''})\n"
    
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
    
    missing_yields = []
    for c in countries:
        local_yield_data = get_te_yield(c["te_path"])
        local_yield, local_cache_date = local_yield_data if local_yield_data else (0.0, False)
        if local_cache_date and local_cache_date != "자료 없음": has_cache = True
        if local_yield == 0.0 or local_cache_date == "자료 없음":
            missing_yields.append(c["name"])
            continue
        
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
        _local_src = YIELD_SOURCE.get(c["te_path"], ("자료 없음", ""))
        _local_src_txt = f"{_local_src[0]}{' ' + _local_src[1] if _local_src[1] else ''}"
        _us_src_txt = f"{_us_src[0]}{' ' + _us_src[1] if _us_src[1] else ''}"
        _spread_contrib = spread * -1.0
        report += f"\n{c['flag']} *{c['name']} ({sym})*{cache_warn}\n"
        report += f" • 환율: {cfx:,.4f} (3개월 전 대비 {trend_word} {abs(raw_fx_change):.2f}%, 유럽중앙은행 고시 {_fx_date})\n"
        report += f" • 금리: 🇺🇸{us_yield:.2f}% ({_us_src_txt}) vs {c['flag']}{local_yield:.2f}% ({_local_src_txt})\n"
        report += f" • 판정: {status} [{final_score:+.2f}%: 환율 {fx_gain_score:+.2f}, 금리차 {_spread_contrib:+.2f}] — 자체 규칙, 투자 신호 아님\n"
        
    if missing_yields:
        report += f"\n금리 자료 없음: {', '.join(missing_yields)} (출처 실패, 기본값 사용 안 함)\n"
    if has_cache:
        report = report.replace("🔄 *[글로벌 B2B 매력도 분석]*", "🔄 *[글로벌 B2B 매력도 분석]*\n🚨 *[주의: API 통신 장애로 일부 국가의 경우 최근 캐시 데이터가 반영되었습니다]*")
        
    return report.strip()


# 감시 단어 목록 (2026-11-06, 파트너님이 직접 정한 88개 + "구글 트렌드" 표기 1개 = 89개).
# 구글 트렌드 Really Simple Syndication 필터와 구글 뉴스 Really Simple Syndication 검색 둘 다 이 목록을 쓴다.
# 목적: 국제 정세와 단어를 빨리 캐치한다.
WATCH_KEYWORDS = [
    "미국 중간선거", "인텔 주가", "중국 증시", "메타 뮤즈", "엔트로픽 상장",
    "샘 알트만 인터뷰", "미국 아이오와 농민", "미국 농민", "미국 금리", "미국 관세",
    "미국 전기차 관세", "미국 공화당 민주당 의석 수", "이스라엘 의석 수", "이스라엘 총리",
    "대한민국 대통령 지지도", "대한민국 사법개혁", "대한민국 대법원장", "대한민국 탄핵",
    "일본 환율", "러시아 전쟁", "러시아 유가", "중국 로봇", "유니트리",
    "중국 AI", "중국 데이터 센터", "미국 데이터 센터", "유럽 금리", "유럽 실업률",
    "유럽 데이터 센터", "아프리카 난민", "이란 난민", "브라질 대두", "브라질 인프라",
    "말레이시아 환율", "태국 국왕", "인도네시아 IT", "중국 국경", "중국 분쟁",
    "대만 군사", "중국 군사", "페트리어트", "토마호크", "개방형 팬",
    "미국 상원", "미국 하원", "QQQ", "VOO", "인텔",
    "HBF", "HBM", "엔비디아", "삼성반도체", "하이닉스",
    "마이크론", "구글 트랜드", "구글 트렌드", "해킹", "코인",
    "커피", "환율", "지방간", "콜레스테롤", "희귀질환 치료제",
    "우롱차", "백차", "DTF 2060", "항공모함", "하드디스크",
    "국채", "SPY", "Dola", "롤스로이스", "마이바흐",
    "샤오미", "3d 프린팅", "F1", "보잉 777", "오설록",
    "아테스토니", "캠리", "어코드", "드론", "어깨 뻐근함",
    "캐나다구스", "보잉 787", "Z flip 8", "클로드", "에르메스",
    "쿠치넬리",
]
TARGET_KEYWORDS = WATCH_KEYWORDS

import re

# 라이프/헬스 분류 키워드 (코드 안에 명시한다. 분류가 안 되면 글로벌 경제로 보낸다.)
LIFE_HEALTH_KEYWORDS = [
    "건강", "의료", "치료제", "신약", "백신", "병원", "식품의약품청", "암", "질병",
    "혈우병", "백질이영양증", "치료", "의사", "운동",
    "health", "medical", "medicine", "drug", "vaccine", "hospital", "disease",
    "cancer", "mental health", "fitness", "doctor", "pharma", "clinical",
]

def classify_trend_category(t):
    text = (t.get("keyword", "") + " " + t.get("summary", "") + " " + " ".join([n.get("title", "") for n in t.get("news", [])])).lower()
    for k in LIFE_HEALTH_KEYWORDS:
        if k.lower() in text:
            return "라이프/헬스"
    return "글로벌 경제"

def filter_trends_by_keywords(trends_list):
    filtered = []
    for t in trends_list:
        text_to_search = (t["keyword"] + " " + " ".join([n["title"] for n in t.get("news", [])])).lower()
        # 키워드 매칭을 먼저 한다. 언어 자체를 빼지 않는다.
        matched_keys = []
        for k in TARGET_KEYWORDS:
            k_lower = k.lower()
            if re.search(r'[a-z]', k_lower):
                if re.search(rf'\b{re.escape(k_lower)}\b', text_to_search):
                    matched_keys.append(k_lower)
            else:
                if k_lower in text_to_search:
                    matched_keys.append(k_lower)
        if not matched_keys:
            continue
        # 외국어 차단은 약하게: 강한 키워드(한글이거나 4자 초과)가 있으면 남기고,
        # 짧고 흔한 영문 단어만으로 걸린 경우에만 외국어 흔적 단어가 있으면 뺀다.
        foreign_stop = [r'\bhet\b', r'\been\b', r'\bbij\b', r'\bund\b', r'\boder\b', r'\bel\b', r'\bla\b', r'\blos\b', r'\blas\b', r'\bpara\b', r'\bcryptobeurs\b']
        is_foreign = any(re.search(fw, text_to_search) for fw in foreign_stop)
        strong = any((len(k) > 4) or re.search(r'[가-힣]', k) for k in matched_keys)
        if is_foreign and not strong:
            continue
        filtered.append(t)
    return filtered

def _parse_traffic(s):
    try:
        return int(str(s).strip().replace(",", "").replace("+", ""))
    except Exception:
        return 0

def _news_domain(url):
    try:
        import urllib.parse as _up
        host = _up.urlparse(url or "").netloc.replace("www.", "")
        return host or "출처 미상"
    except Exception:
        return "출처 미상"

# 출판사 이름 표시 (랙스다 전용, SHOW_PUBLISHER_NAMES=true일 때만 켠다).
# 표 파일 Sheet2의 46개 미디어 이름 목록(2026-11-06)에서 만든 대응표.
# 전자신문은 etnews.com, 이데일리는 edaily.co.kr로 바로잡았다.
# magazine.hankyung.com은 한경비즈니스, mbn 계열은 MBN으로 맞췄다.
# 동행미디어 시대는 주소를 몰라서 넣지 않았다.
PUBLISHER_NAMES = {
    "hankyung.com": "한국경제",
    "magazine.hankyung.com": "한경비즈니스",
    "sedaily.com": "서울경제",
    "biz.heraldcorp.com": "헤럴드경제",
    "seoul.co.kr": "서울신문",
    "etnews.com": "전자신문",
    "edaily.co.kr": "이데일리",
    "yna.co.kr": "연합뉴스",
    "yonhapnewstv.co.kr": "연합뉴스TV",
    "mk.co.kr": "매일경제",
    "economy.mk.co.kr": "매경이코노미",
    "joongang.co.kr": "중앙일보",
    "newsis.com": "뉴시스",
    "munhwa.com": "문화일보",
    "mt.co.kr": "머니투데이",
    "segye.com": "세계일보",
    "hani.co.kr": "한겨레",
    "nocutnews.co.kr": "노컷뉴스",
    "zdnet.co.kr": "지디넷코리아",
    "busan.com": "부산일보",
    "news1.kr": "뉴스1",
    "dt.co.kr": "디지털타임스",
    "bloter.net": "블로터",
    "biz.chosun.com": "조선비즈",
    "chosun.com": "조선일보",
    "weekly.chosun.com": "주간조선",
    "mbn.mk.co.kr": "MBN",
    "mbn.co.kr": "MBN",
    "economist.co.kr": "이코노미스트",
    "khan.co.kr": "경향신문",
    "kbs.co.kr": "KBS",
    "sbs.co.kr": "SBS",
    "biz.sbs.co.kr": "SBS Biz",
    "tvchosun.com": "TV조선",
    "ytn.co.kr": "YTN",
    "kado.net": "강원도민일보",
    "kmib.co.kr": "국민일보",
    "dgmbc.com": "대구MBC",
    "tf.co.kr": "더팩트",
    "dailian.co.kr": "데일리안",
    "ddaily.co.kr": "디지털데일리",
    "asiae.co.kr": "아시아경제",
    "inews24.com": "아이뉴스24",
    "fnnews.com": "파이낸셜뉴스",
    "wowtv.co.kr": "한국경제TV",
    "hankookilbo.com": "한국일보",
}

def _publisher_label(url):
    dom = _news_domain(url)
    if os.environ.get("SHOW_PUBLISHER_NAMES", "").strip().lower() != "true":
        return dom
    if dom in PUBLISHER_NAMES:
        return PUBLISHER_NAMES[dom]
    # 하위 주소도 잡는다: en.sedaily.com -> sedaily.com -> 서울경제.
    # 왼쪽부터 한 개씩 떼어 보되, 등록 가능한 주소보다 짧아지면 멈춘다.
    # (.co.kr 주소는 3개까지만 떼고, 그 아래는 주소로 둔다.)
    labels = dom.split(".")
    for i in range(1, len(labels)):
        cand = ".".join(labels[i:])
        if len(cand.split(".")) < 2:
            break
        if dom.endswith(".co.kr") and len(cand.split(".")) < 3:
            break
        if cand in PUBLISHER_NAMES:
            return PUBLISHER_NAMES[cand]
    return dom

def _normalize_title(s):
    return re.sub(r'[^a-z0-9가-힣]+', '', (s or "").lower())

def summarize_all_trends(all_trends_info):
    # LLM removed as per user instruction. Fast fallback to news titles.
    for t in all_trends_info:
        t["summary"] = t["news"][0]["title"] if t["news"] else "관련 뉴스 없음"
    return all_trends_info

def get_google_trends_raw(geo="KR", limit=5):
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        res = _fetch_with_retry(url, timeout=10)
        if res is None or res.status_code != 200: return []
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

# 추적 키워드 13개 (표 파일의 키워드 목록). 구글 뉴스 RSS에서 직접 가져온다.
TRACK_KEYWORDS = TARGET_KEYWORDS

def get_keyword_news(keyword, limit=5):
    # 구글 뉴스 RSS 검색: 키워드별 최신 기사. 46개 언론사 기사를 포함한다.
    import urllib.parse as _up
    url = "https://news.google.com/rss/search?q=" + _up.quote(keyword) + "&hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = _fetch_with_retry(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if res is None or res.status_code != 200:
            return None
        root = ET.fromstring(res.text)
        channel = root.find("channel")
        if channel is None:
            return None
        news_list = []
        for item in channel.findall("item")[:limit]:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            src = item.find("source").text if item.find("source") is not None else ""
            if title and link:
                news_list.append({"title": title, "url": link, "source": src})
        if not news_list:
            return None
        return {
            "keyword": keyword,
            "traffic": "",
            "search_link": "https://news.google.com/search?q=" + _up.quote(keyword),
            "news": news_list,
            "geo_name": "South Korea",
        }
    except Exception as e:
        print(f"Keyword news error ({keyword}):", e)
        return None

# 주제별 묶음 (2026-11-06). 가독성을 위해 2개 카테고리 대신 10개 주제로 나눈다.
# 각 주제는 감시 단어 목록의 단어들로 정한다. 항목은 가장 먼저 맞는 주제에 들어간다.
# 스크롤이 길어져도 주제 머리말과 한눈에 보기로 문맥을 쉽게 파악한다.
THEMES = [
    ("🇺🇸 미국 정치", ["미국 중간선거", "미국 상원", "미국 하원", "미국 공화당 민주당 의석 수"]),
    ("🇺🇸 미국 경제", ["미국 금리", "미국 관세", "미국 전기차 관세", "미국 농민", "미국 아이오와 농민"]),
    ("🇨🇳 중국", ["중국 증시", "중국 로봇", "유니트리", "중국 AI", "중국 데이터 센터", "중국 국경", "중국 분쟁", "중국 군사", "대만 군사", "샤오미"]),
    ("🌍 지정학/안보", ["러시아 전쟁", "러시아 유가", "이스라엘 의석 수", "이스라엘 총리", "페트리어트", "토마호크", "항공모함", "해킹", "드론"]),
    ("💻 반도체/AI", ["인텔", "인텔 주가", "엔비디아", "삼성반도체", "하이닉스", "마이크론", "HBM", "HBF", "클로드", "메타 뮤즈", "엔트로픽 상장", "샘 알트만 인터뷰", "Dola", "미국 데이터 센터", "개방형 팬"]),
    ("📈 시장/금융", ["QQQ", "VOO", "SPY", "국채", "환율", "코인", "일본 환율", "말레이시아 환율"]),
    ("🇰🇷 한국", ["대한민국 대통령 지지도", "대한민국 사법개혁", "대한민국 대법원장", "대한민국 탄핵"]),
    ("🇪🇺 유럽", ["유럽 금리", "유럽 실업률", "유럽 데이터 센터"]),
    ("🌏 기타 지역", ["아프리카 난민", "이란 난민", "브라질 대두", "브라질 인프라", "태국 국왕", "인도네시아 IT"]),
    ("☕ 생활/소비/건강", ["커피", "지방간", "콜레스테롤", "희귀질환 치료제", "우롱차", "백차", "DTF 2060", "하드디스크", "롤스로이스", "마이바흐", "3d 프린팅", "F1", "보잉 777", "오설록", "아테스토니", "캠리", "어코드", "어깨 뻐근함", "캐나다구스", "보잉 787", "Z flip 8", "에르메스", "쿠치넬리", "구글 트랜드", "구글 트렌드"]),
]

# 구글 트렌드 24시간 활성 트렌드 (생활/소비/건강 하단, 2026-11-06).
# Really Simple Syndication은 지금 뜨는 검색어(24시간, 활성 트렌드)를 돌려준다. 필터를 거치지 않은 날것을 쓴다.
GT24_REGIONS = [
    ("🇺🇸 미국", "California (US)"),
    ("🇸🇬 싱가포르", "Singapore"),
    ("🇰🇷 대한민국", "South Korea"),
    ("🇳🇱 네덜란드", "Netherlands"),
]

def _build_google_trends_24h(raw_trends, top_n=8):
    # 구글 트렌드 날것(필터 전)을 지역별로 묶어 24시간 활성 트렌드만 보여준다.
    by_region = {}
    for t in raw_trends or []:
        by_region.setdefault(t.get("geo_name", ""), []).append(t)
    lines = []
    for _flag, _geo in GT24_REGIONS:
        _items = by_region.get(_geo, [])
        if not _items:
            continue
        _items = sorted(_items, key=lambda x: -(_parse_traffic(x.get("traffic", "")) or 0))[:top_n]
        _parts = []
        for _it in _items:
            _kw = _it["keyword"]
            _tr = _it.get("traffic", "")
            _tr_txt = f"({_tr}+)" if _tr else ""
            _parts.append(f"{_safe_mrkdwn_link(_it.get('search_link', ''), _kw)} {_tr_txt}".strip())
        lines.append(f"{_flag}: " + " · ".join(_parts))
    if not lines:
        return []
    return [{
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*📈 구글 트렌드 24시간 · 활성 트렌드만*\n" + "\n".join(lines)}
    }]

# --- 자동 복구: 다시 시도와 상태 기록 ---
# 에러는 생긴다. 이를 인지하고 자동으로 다시 시도하는 것이 포인트다.
def _fetch_with_retry(url, headers=None, timeout=10, max_retries=3):
    # 가져오기를 다시 시도한다. 일시적인 네트워크 오류와 5xx, 429번에 다시 시도한다.
    # 400번(잘못된 요청)은 다시 시도해도 안 되므로 바로 돌려준다.
    _delay = 5
    for _attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=timeout)
            if res.status_code == 200:
                return res
            if res.status_code in (429, 500, 502, 503, 504) and _attempt < max_retries - 1:
                print(f"가져오기 {res.status_code}, {_delay}초 뒤 다시 시도 ({_attempt + 1}/{max_retries})")
                time.sleep(_delay)
                _delay *= 2
                continue
            return res
        except Exception as e:
            if _attempt < max_retries - 1:
                print(f"가져오기 오류 {e}, {_delay}초 뒤 다시 시도 ({_attempt + 1}/{max_retries})")
                time.sleep(_delay)
                _delay *= 2
                continue
            print(f"가져오기 실패 (다시 시도 {max_retries}번): {e}")
            return None
    return None

def _post_with_retry(url, payload, max_retries=3):
    # 슬랙 보내기를 다시 시도한다. 5xx와 429번, 네트워크 오류에 다시 시도한다.
    # 400번(잘못된 요청)은 다시 시도해도 안 되므로 바로 돌려준다.
    _delay = 10
    _last = None
    for _attempt in range(max_retries):
        try:
            res = requests.post(url, json=payload, timeout=10)
            _last = res
            if res.status_code == 200:
                return res
            if res.status_code in (429, 500, 502, 503, 504) and _attempt < max_retries - 1:
                print(f"슬랙 보내기 {res.status_code}, {_delay}초 뒤 다시 시도 ({_attempt + 1}/{max_retries})")
                time.sleep(_delay)
                _delay *= 2
                continue
            return res
        except Exception as e:
            if _attempt < max_retries - 1:
                print(f"슬랙 보내기 오류 {e}, {_delay}초 뒤 다시 시도 ({_attempt + 1}/{max_retries})")
                time.sleep(_delay)
                _delay *= 2
                continue
            print(f"슬랙 보내기 실패 (다시 시도 {max_retries}번): {e}")
            return _last
    return _last

def _write_push_status(mode, b2b_status, trends_status, errors):
    # 이번 실행 결과를 상태 파일에 남긴다. 감시 스크립트가 이 파일을 보고 실패를 알아챈다.
    try:
        _dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(_dir, exist_ok=True)
        _status = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode,
            "b2b_status": b2b_status,
            "trends_status": trends_status,
            "ok": (b2b_status in (200, None)) and (trends_status in (200, None)) and not errors,
            "errors": errors,
        }
        with open(os.path.join(_dir, "last_push_status.json"), "w", encoding="utf-8") as f:
            json.dump(_status, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("상태 파일 쓰기 실패:", e)

def _theme_for(t):
    # 항목이 어느 주제에 들어가는지 정한다. 단어와 요약, 첫 기사 제목에서 주제 단어를 찾는다.
    _txt = (t.get("keyword", "") + " " + t.get("summary", "")).lower()
    if t.get("news"):
        _txt += " " + t["news"][0]["title"].lower()
    for _name, _kws in THEMES:
        for _kw in _kws:
            if _kw.lower() in _txt:
                return _name
    return "📌 기타"

# --- 가드레일: 오늘 겪은 에러를 자동으로 막는다 ---
def _safe_mrkdwn_link(url, text):
    # 슬랙 마크다운 링크 안의 주소에 &가 있으면 400번 오류가 난다. &를 %26으로 바꾼다.
    safe = (url or "").replace("&", "%26")
    return f"<{safe}|{text}>"

def _split_long_sections(blocks, limit=2800):
    # 어떤 구역이든 3000자를 넘지 않게 나눈다. 자동 수정 가드레일.
    # 구역 나누기가 개수 기준이라 긴 제목이 3000자를 넘긴 오늘의 400번 오류를 막는다.
    out = []
    for b in blocks:
        if b.get("type") != "section":
            out.append(b)
            continue
        text = b.get("text", {}).get("text", "")
        if len(text) <= limit:
            out.append(b)
            continue
        lines = text.split("\n")
        header = lines[0]
        items = lines[1:]
        cur = [header]
        cur_len = len(header)
        for it in items:
            if cur_len + 1 + len(it) > limit and len(cur) > 1:
                out.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(cur)}})
                cur = [header + " (계속)"]
                cur_len = len(cur[0])
            cur.append(it)
            cur_len += 1 + len(it)
        if cur:
            out.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(cur)}})
    return out

def _validate_payload(payload):
    # 보내기 전 최종 검사. 문제를 찾으면 그 내용을 돌려준다.
    problems = []
    if not payload:
        return problems
    blocks = payload.get("blocks", [])
    if len(blocks) > 50:
        problems.append(f"블록 {len(blocks)}개가 50개 제한을 넘는다")
    for b in blocks:
        if b.get("type") == "section":
            t = b.get("text", {}).get("text", "")
            if len(t) > 3000:
                problems.append(f"구역 {len(t)}자가 3000자 제한을 넘는다")
            for u in re.findall(r"<(https?://[^>|]+)", t):
                if "&" in u:
                    problems.append(f"링크 주소에 &가 있다: {u[:80]}")
    return problems

def send_slack():
    SENT_URLS = load_history()
    NEW_SENT_URLS = set()
    # 푸시 모드: both(기본, 둘 다), b2b(기업 간 거래만), trends(소식만).
    # 라즈베리는 b2b, 랙스다는 trends로 둔다. 모르는 값은 둘 다로 둔다.
    _mode = os.environ.get("PUSH_MODE", "both").strip().lower()
    do_b2b = _mode != "trends"
    do_trends = _mode != "b2b"
    payload_b2b = None
    payload_trends = None
    summarized_all = []

    if do_b2b:
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
                            "text": f"🎯 F5 B2B 분석 (발행: {datetime.now().strftime('%m/%d %H:%M')})"
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

    
    # 구글 트렌드 24시간 활성 트렌드 (생활/소비/건강 하단에 붙인다). 필터를 거치기 전의 날것을 둔다.
    _gt4_geos = {"California (US)", "Singapore", "South Korea", "Netherlands"}
    raw_trends_4 = [t for t in all_trends if t.get("geo_name") in _gt4_geos]

    all_trends = filter_trends_by_keywords(all_trends)
    # 추적 키워드 13개는 구글 뉴스 RSS에서 직접 가져온다. 목표 키워드 필터를 거치지 않는다.
    for _kw in TRACK_KEYWORDS:
        _kn = get_keyword_news(_kw)
        if _kn:
            all_trends.append(_kn)
    summarized_all = summarize_all_trends(all_trends)

    # 중복 방지: 이미 보낸 뉴스 주소는 다시 보내지 않는다.
    # sent_history.json은 data 폴더에 두어 컨테이너가 다시 떠도 남는다.
    summarized_all = [
        t for t in summarized_all
        if not t.get("news") or t["news"][0].get("url") not in SENT_URLS
    ]
    # 같은 정규화 제목은 한 번만 남기고, 몇 개 지역에서 나왔는지 센다.
    # (이미 보낸 URL을 먼저 거른 뒤에 중복을 합친다. 먼저 합치면 안 보낸 복사본까지 사라진다.)
    _seen_norm = {}
    deduped_all = []
    for _t in summarized_all:
        _first_title = _t["news"][0]["title"] if _t.get("news") else _t.get("keyword", "")
        _norm = _normalize_title(_first_title) or _normalize_title(_t.get("keyword", ""))
        if _norm and _norm in _seen_norm:
            _seen_norm[_norm]["geo_count"] = _seen_norm[_norm].get("geo_count", 1) + 1
            _seen_norm[_norm].setdefault("geos", []).append(_t.get("geo_name", ""))
            continue
        _t["geo_count"] = 1
        _t["geos"] = [_t.get("geo_name", "")]
        if _norm:
            _seen_norm[_norm] = _t
        deduped_all.append(_t)
    summarized_all = deduped_all
    for _t in summarized_all:
        _t["category"] = classify_trend_category(_t)
    # 핵심 키워드 Top 10 (검색량 가중치). 감시 단어 구절을 세어 소식 보고서와 기업 간 거래 보고서 둘 다 하단에 붙인다.
    _scores = {}
    for _t in summarized_all:
        _txt = _t["keyword"] + " " + _t.get("summary", "")
        for _n in _t["news"]:
            _txt += " " + _n["title"]
        _low = _txt.lower()
        _w = _parse_traffic(_t.get("traffic", "")) or 1
        for _kw in TARGET_KEYWORDS:
            if _kw.lower() in _low:
                _scores[_kw] = _scores.get(_kw, 0) + _w
    _top10 = sorted(_scores.items(), key=lambda kv: -kv[1])[:10]
    top10_str = " | ".join([f"*{w}*({c})" for w, c in _top10]) if _top10 else ""

    
    # 주제별 묶음. 가독성을 위해 2개 카테고리 대신 10개 주제로 나눈다.
    # 스크롤이 길어져도 주제 머리말과 한눈에 보기로 문맥을 쉽게 파악한다.
    if do_trends:
        trends_by_theme = {}
        for _name, _kws in THEMES:
            trends_by_theme[_name] = []
        trends_by_theme["📌 기타"] = []

        geo_short = {
            "South Korea": "KR", "Singapore": "SG", "Netherlands": "NL",
            "Hong Kong": "HK", "Switzerland": "CH", "Israel": "IL",
            "Japan": "JP", "California (US)": "US"
        }

        for t in summarized_all:
            g = geo_short.get(t['geo_name'], t['geo_name'])
            kw = t["keyword"]
            s_link = t["search_link"]
            summary = t["summary"]
            top_news_url = t["news"][0]["url"] if t["news"] else s_link
            _traf = t.get("traffic", "")
            _traf_txt = f"검색량 {_traf}+" if _traf else "검색량 미상"
            _src = t["news"][0].get("source") if t.get("news") else None
            _dom = _src if _src else _publisher_label(top_news_url)
            _geo_txt = f", {t.get('geo_count', 1)}개 지역" if t.get("geo_count", 1) > 1 else ""
            # 한 항목을 두 줄로 쓴다. 첫 줄은 단어와 지역, 검색량. 둘째 줄은 기사 제목과 출처.
            _item = (
                f"• {_safe_mrkdwn_link(s_link, '*' + kw + '*')} [{g}] · {_traf_txt}{_geo_txt}\n"
                f"↳ {_safe_mrkdwn_link(top_news_url, summary)} (출처: {_dom})"
            )
            trends_by_theme[_theme_for(t)].append(_item)

        trends_blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🌐 글로벌 이슈 트래킹"}
            }
        ]

        # 한눈에 보기: 주제별 건수
        _ov_parts = []
        for _name, _items in trends_by_theme.items():
            if _items:
                _ov_parts.append(f"{_name} {len(_items)}건")
        if _ov_parts:
            trends_blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "📌 오늘의 한눈에 보기: " + " · ".join(_ov_parts)}]
            })

        _gt24_added = False
        for _name, _items in trends_by_theme.items():
            if not _items:
                continue
            # 3000자 제한: 주제 안에서 글자 수 기준으로 나눈다.
            _chunks = []
            _cur = []
            _cur_len = 0
            for _it in _items:
                _it_len = len(_it) + 1
                if _cur and _cur_len + _it_len > 2800:
                    _chunks.append(_cur)
                    _cur = []
                    _cur_len = 0
                _cur.append(_it)
                _cur_len += _it_len
            if _cur:
                _chunks.append(_cur)
            for _ci, _chunk in enumerate(_chunks):
                header_text = f"*{_name} ({len(_items)}건)*" if _ci == 0 else f"*{_name}* (계속)"
                trends_blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": header_text + "\n" + "\n".join(_chunk)}
                })
            # 생활/소비/건강 주제 바로 아래에 구글 트렌드 24시간 활성 트렌드를 붙인다.
            if _name == "☕ 생활/소비/건강":
                trends_blocks.extend(_build_google_trends_24h(raw_trends_4))
                _gt24_added = True

        # 생활/소비/건강 주제에 항목이 없어서 위에서 안 붙었다면, 주제들 뒤에 붙인다.
        if not _gt24_added:
            trends_blocks.extend(_build_google_trends_24h(raw_trends_4))

        if top10_str:
            trends_blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"🔥 *오늘의 핵심 키워드 Top 10*: {top10_str}"}]
            })

        payload_trends = {"text": "글로벌 트렌드 분석", "blocks": trends_blocks}
    if do_b2b and payload_b2b and top10_str:
        payload_b2b["blocks"].append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"🔥 *오늘의 핵심 키워드 Top 10*: {top10_str}"}]
        })
    
    # 가드레일: 보내기 전에 모든 구역을 2800자 이하로 다시 나눈다. 자동 수정.
    if payload_b2b:
        payload_b2b["blocks"] = _split_long_sections(payload_b2b["blocks"])
    if payload_trends:
        payload_trends["blocks"] = _split_long_sections(payload_trends["blocks"])
    # 가드레일: 자동 수정 뒤에도 문제가 남으면 그 보고서는 보내지 않는다. 다음 실행 때 다시 보낸다.
    if payload_b2b:
        _p = _validate_payload(payload_b2b)
        if _p:
            print("기업 간 거래 보고서 검사 실패, 보내지 않는다:", _p)
            payload_b2b = None
    if payload_trends:
        _p = _validate_payload(payload_trends)
        if _p:
            print("소식 보고서 검사 실패, 보내지 않는다:", _p)
            payload_trends = None

    # [E2E 텍스트 풀-프린트 검증]
    if do_b2b:
        print("--- PAYLOAD 1: B2B ---")
        print(json.dumps(payload_b2b, ensure_ascii=False, indent=2))
    if do_trends:
        print("--- PAYLOAD 2: TRENDS ---")
        print(json.dumps(payload_trends, ensure_ascii=False, indent=2))
    print("------------------------")
    
    _b2b_status = None
    _trends_status = None
    _errors = []
    if SLACK_WEBHOOK_URL:
        try:
            _sent_ok = True
            if payload_b2b:
                res1 = _post_with_retry(SLACK_WEBHOOK_URL, payload_b2b)
                _b2b_status = res1.status_code if res1 is not None else None
                print("B2B 전송:", _b2b_status)
                _sent_ok = _sent_ok and _b2b_status == 200
                if _b2b_status != 200:
                    _errors.append(f"B2B 전송 {_b2b_status}")
            if payload_trends:
                res2 = _post_with_retry(SLACK_WEBHOOK_URL, payload_trends)
                _trends_status = res2.status_code if res2 is not None else None
                print("Trends 전송:", _trends_status)
                _sent_ok = _sent_ok and _trends_status == 200
                if _trends_status != 200:
                    _errors.append(f"Trends 전송 {_trends_status}")
            # 전송이 실패하면 보낸 기록을 저장하지 않는다. 다음 실행 때 다시 보낸다.
            if _sent_ok:
                for t in summarized_all:
                    if t["news"]: NEW_SENT_URLS.add(t["news"][0]["url"])
                SENT_URLS.update(NEW_SENT_URLS)
                save_history(SENT_URLS)
            else:
                print("전송 실패: 보낸 기록을 저장하지 않는다.")
        except Exception as e:
            print("Slack 발송 에러:", e)
            _errors.append(f"Slack 발송 에러: {e}")
    else:
        _errors.append("SLACK_WEBHOOK_URL이 비어 있다")
    # 이번 실행 결과를 상태 파일에 남긴다. 감시 스크립트가 이 파일을 보고 실패를 알아챈다.
    _write_push_status(_mode, _b2b_status, _trends_status, _errors)

if __name__ == "__main__":
    send_slack()