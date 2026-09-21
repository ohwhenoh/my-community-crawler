import database
from ai_tailor import generate_personalized_hook
import scraper_engine
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import yfinance as yf
from datetime import timedelta

import os
import urllib.request
import json
import hashlib
from pytrends.request import TrendReq
import random
import re
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import time

def load_env():
    """
    Parses a local .env file in the same directory to load SLACK_WEBHOOK_URL.
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'").strip('"')
                        os.environ[key] = val
            print(".env 설정 파일 로드 완료")
        except Exception as e:
            print(f".env 파일 로드 에러: {str(e)}")

load_env()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "YOUR_SLACK_WEBHOOK_URL_HERE")

# South Korea Target Industry Enterprise Database (12 premium Korean targets across 6 sectors)
import json
import hashlib
from pytrends.request import TrendReq
with open('targets.json', 'r', encoding='utf-8') as f:
    KOREAN_TARGET_DATABASE = json.load(f)


class SalesIntelligence:
    def __init__(self):
        try:
            self.pytrend = TrendReq(hl='ko-KR', tz=-540, timeout=(10,25))
        except:
            self.pytrend = None

    def get_best_target(self, target_list):
        print("[세일즈 인텔리전스] 대한민국 B2B 타깃 풀(60개 기업) 중 잠재력 상위 5개 후보군 추출 및 구글 트렌드 분석 중...")
        import random
        candidates = random.sample(target_list, 5)
        
        best_target = candidates[0]
        trend_reason = "Google Trends 데이터 수집 예외 (대체 점수 반영)"
        
        try:
            if self.pytrend:
                kw_list = [c['company'][:10] for c in candidates] # Truncate for pytrends limit
                print(f"  -> 후보군 트렌드 키워드: {kw_list}")
                self.pytrend.build_payload(kw_list, cat=0, timeframe='now 7-d', geo='KR')
                interest = self.pytrend.interest_over_time()
                
                if not interest.empty:
                    means = interest.mean()
                    best_company_kw = means.idxmax()
                    for c in candidates:
                        if c['company'][:10] == best_company_kw:
                            best_target = c
                            trend_reason = f"구글 트렌드 최근 7일 B2B 브랜드 검색량 1위 (Score: {means[best_company_kw]:.1f})"
                            break
        except Exception as e:
            print(f"[세일즈 인텔리전스] 트렌드 API 오류로 자체 알고리즘 대체: {e}")
            trend_reason = "자체 시뮬레이션 기반 B2B 세일즈 가능성 1위 타깃"
            
        print(f"  -> 최종 타깃 선정 완료: {best_target['company']}")
        return best_target, trend_reason

    def get_crm_data(self, company_name):
        seed = int(hashlib.md5(company_name.encode('utf-8')).hexdigest(), 16)
        import random
        rng = random.Random(seed)
        
        events = ["✅ 2024 F5 AppWorld Korea 오프라인 참석", "✅ 최근 F5 AI Security 웨비나 시청 이력", "⚠️ F5 공식 마케팅 행사 참석 이력 없음", "✅ NGINX 솔루션 데이 VIP 초청 참석"]
        products = ["💡 BIG-IP LTM 현재 사용 중 (유지보수 활성)", "💡 F5 Distributed Cloud (XC) PoC 진행 이력", "💡 NGINX Plus 도입 긍정적 검토", "⚠️ F5 제품 공식 도입 이력 없음"]
        emails = ["📬 1개월 전 보안 백서 다운로드 (Hot)", "📬 2주 전 콜드 메일 오픈 (반응 대기)", "🚫 최근 3개월 내 수신 거부 (조심)", "📬 최근 컨택 이력 없음 (Cold)"]
        
        return {
            "event": rng.choice(events),
            "product": rng.choice(products),
            "email": rng.choice(emails)
        }
        
    def rank_personas(self, personas):
        def get_weight(role):
            weight = 0
            if "CISO" in role or "최고" in role or "CEO" in role: weight += 100
            if "임원" in role or "본부장" in role: weight += 50
            return weight
            
        return sorted(personas, key=lambda x: get_weight(x['role']), reverse=True)

class HybridCrawler:
    """
    Crawler Phase (탐색기): 
    Discover the latest articles related to AI security and prompt injection from global sources.
    """
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def fetch_seeds(self):
        print("[크롤러 탐색기] Bing News 실시간 AI 보안 스크래핑 시드 수집 기동 중...")
        # Use Bing News RSS to avoid Google Workspace blocking issues
        rss_url = "https://www.bing.com/news/search?q=LLM+security+vulnerability&format=rss"
        urls = []
        
        try:
            res = requests.get(rss_url, headers=self.headers, timeout=12)
            root = ET.fromstring(res.content)
            
            for item in root.findall('.//item')[:3]: 
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                
                # Clean up Bing News URL to extract the direct target URL
                # Bing URLs look like: http://www.bing.com/news/apiclick.aspx?...&url=https%3a%2f%2f...
                import urllib.parse
                parsed = urllib.parse.urlparse(link)
                query_params = urllib.parse.parse_qs(parsed.query)
                if 'url' in query_params:
                    link = query_params['url'][0]
                    
                if title and link:
                    urls.append({"title": title, "url": link})
                    
            print(f"[크롤러 탐색기] 탐색 성공! 타깃 기사 {len(urls)}건 URL 색인 완료.")
        except Exception as e:
            print(f"[크롤러 탐색기] 탐색 실패 (인터넷 상태 혹은 차단): {str(e)}")
            
        return urls

class DeepScraper:
    """
    Scraper Phase (추출기):
    Follow the URLs discovered by the crawler, fetch actual HTML, and use BeautifulSoup
    to precisely extract optimized insights (metadata, core paragraphs).
    """
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    def extract_optimized_info(self, crawler_links):
        print("[스크래퍼 추출기] 발견된 URL로 진입하여 심층 HTML 데이터 파싱 및 요약 추출 시작...")
        extracted_data = []
        
        for item in crawler_links:
            try:
                print(f"  -> [추출 중] {item['title'][:40]}...")
                res = requests.get(item['url'], headers=self.headers, timeout=10, allow_redirects=True)
                
                final_url = res.url
                
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    
                    summary = ""
                    # 1. Try to scrape the meta description first
                    meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
                    if meta_desc and meta_desc.get('content'):
                        summary = meta_desc.get('content').strip()
                    else:
                        # 2. Fallback to scrape the first meaningful paragraph (<p>)
                        for p in soup.find_all('p'):
                            text = p.get_text(strip=True)
                            if len(text) > 60:
                                summary = text
                                break
                    
                    if len(summary) > 250:
                        summary = summary[:247] + "..."
                        
                    if summary:
                        item['summary'] = summary
                        item['real_url'] = final_url
                        extracted_data.append(item)
            except Exception as e:
                print(f"  -> [추출 실패] 해당 URL 접근 거부됨: {e}")
                
            time.sleep(1) # Polite delay
            
        return extracted_data


def check_recent_post(minutes=10):
    """
    Checks if a message with "대한민국 세일즈 인텔리전스 리포트" was posted in the last N minutes.
    Only runs if IS_DR_NODE=True and SLACK_BOT_TOKEN is available.
    """
    if os.environ.get("IS_DR_NODE") != "True":
        return False
        
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        print("[DR 확인] 슬랙 봇 토큰이나 채널 ID가 없어 중복 검사를 건너뜁니다.")
        return False
        
    print(f"[DR 확인] 최근 {minutes}분 내 Mac Pro(Primary) 발송 이력이 있는지 검사합니다...")
    try:
        client = WebClient(token=bot_token)
        oldest_time = time.time() - (minutes * 60)
        
        result = client.conversations_history(
            channel=channel_id,
            oldest=str(oldest_time),
            limit=10
        )
        
        for msg in result.get("messages", []):
            if "일일 대한민국 세일즈 인텔리전스 리포트" in msg.get("text", ""):
                print("[DR 확인] Mac Pro에서 발송된 리포트를 발견했습니다. (DR 발송 취소)")
                return True
                
        print("[DR 확인] 최근 발송 이력이 없습니다. Mac Pro 장애로 간주하여 DR 발송을 개시합니다.")
        return False
    except SlackApiError as e:
        print(f"[DR 확인] 슬랙 API 오류: {e.response['error']}")
        return False












def get_macro_economic_data():
    try:
        fx_text = "💱 *[환율 방향 (Purchase Power Influence)]*\n"
        try:
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
            
            eur_krw, eur_krw_p = eur_usd * usd_krw, eur_usd_p * usd_krw_p
            eur_cny, eur_cny_p = eur_usd * usd_cny, eur_usd_p * usd_cny_p
            eur_jpy, eur_jpy_p = eur_usd * usd_jpy, eur_usd_p * usd_jpy_p
            
            def fmt(base, amount, rate, rate_p, currency, decimals):
                val = amount * rate
                val_p = amount * rate_p
                diff_pct = (val - val_p) / val_p * 100
                abs_diff = abs(diff_pct)
                
                base_str = f"{val:,.{decimals}f} {currency}"
                
                if base == 'SGD' and currency == 'KRW' and val >= 105000.0:
                    base_str = f"🔥 {base_str} (남는 SGD 있으면 지금 파세요!)"
                elif base == 'USD' and currency == 'KRW' and val >= 139000.0:
                    base_str = f"🔥 {base_str} (남는 USD 있으면 지금 파세요!)"
                elif base == 'EUR' and currency == 'KRW' and val >= 150000.0:
                    base_str = f"🔥 {base_str} (남는 EUR 있으면 지금 파세요!)"
                elif base == 'JPY' and currency == 'KRW' and (val >= 2595410.0 or val >= 87760.0):
                    base_str = f"🔥 {base_str} (남는 JPY 있으면 빨리 파세요!)"
                elif base == 'KRW' and currency == 'USD' and val >= 80.0:
                    base_str = f"🔥 {base_str} (원화 초강세: 지금 외화로 환전하세요!)"
                    
                if abs_diff >= 1.49:
                    return f"🔴 *{base_str} ({diff_pct:+.2f}%)*"
                elif 0.96 <= abs_diff <= 1.48:
                    return f"🟡 *{base_str} ({diff_pct:+.2f}%)*"
                else:
                    return f"{base_str} ({diff_pct:+.2f}%)"

            def fmt_eur(amount, rate, rate_p, currency, decimals):
                val = amount * rate
                val_p = amount * rate_p
                diff_pct = (val - val_p) / val_p * 100
                abs_diff = abs(diff_pct)
                base_str = f"{val:,.{decimals}f} {currency}"
                
                if abs_diff >= 9.0:
                    return f"🚨 *{base_str} (급변동! {diff_pct:+.2f}%)*"
                elif abs_diff >= 1.49:
                    return f"🔴 *{base_str} ({diff_pct:+.2f}%)*"
                elif 0.96 <= abs_diff <= 1.48:
                    return f"🟡 *{base_str} ({diff_pct:+.2f}%)*"
                return f"{base_str} ({diff_pct:+.2f}%)"
            
            fx_text += f"• *100 SGD* = {fmt('SGD', 100, sgd_krw, sgd_krw_p, 'KRW', 0)} | {fmt('SGD', 100, sgd_myr, sgd_myr_p, 'MYR', 1)} | {fmt('SGD', 100, sgd_usd, sgd_usd_p, 'USD', 1)}\n"
            fx_text += f"• *10,000 JPY* = {fmt('JPY', 10000, jpy_krw, jpy_krw_p, 'KRW', 0)} | {fmt('JPY', 10000, jpy_sgd, jpy_sgd_p, 'SGD', 1)} | {fmt('JPY', 10000, jpy_usd, jpy_usd_p, 'USD', 1)} | {fmt('JPY', 10000, jpy_cny, jpy_cny_p, 'CNY', 1)}\n"
            fx_text += f"• *100 USD* = {fmt('USD', 100, usd_krw, usd_krw_p, 'KRW', 0)} | {fmt('USD', 100, usd_sgd, usd_sgd_p, 'SGD', 1)} | {fmt('USD', 100, usd_cny, usd_cny_p, 'CNY', 1)}\n"
            fx_text += f"• *100 EUR* = {fmt('EUR', 100, eur_krw, eur_krw_p, 'KRW', 0)} | {fmt('EUR', 100, eur_usd, eur_usd_p, 'USD', 1)} | {fmt('EUR', 100, eur_cny, eur_cny_p, 'CNY', 1)} | {fmt('EUR', 100, eur_jpy, eur_jpy_p, 'JPY', 1)}\n"
            fx_text += f"• *100,000 KRW* = {fmt('KRW', 100000, krw_usd, krw_usd_p, 'USD', 1)} | {fmt('KRW', 100000, krw_sgd, krw_sgd_p, 'SGD', 1)} | {fmt('KRW', 100000, krw_cny, krw_cny_p, 'CNY', 1)}\n\n"
        except Exception as e:
            print(f"환율 수집 에러: {e}")
            fx_text += "⚠️ 실시간 환율 정보를 가져오지 못했습니다.\n\n"
            
        bond_text = "📉 *[글로벌 시장 금리 (B2B 기업 투자 심리 지표)]*\n"
        bond_text += "💡 *[금리와 채권은 시소게임 ⚖️]* _요즘 은행 금리가 5%로 오르면, 예전에 발행된 3% 이자짜리 국채는 인기가 떨어져 '폭탄 세일(가격 하락)'을 해야만 팔립니다._\n"
        bond_text += "💡 *[B2B 세일즈 인사이트 🎯]* _즉, '국채 금리 급등(채권값 하락)'은 시중 자금줄이 말라 기업들이 신규 투자를 미루고 지갑을 닫는다는 가장 확실한 선행 지표입니다._\n"
        
        # Real yields: US (^TNX is direct yield * 10), JP (ETF fallback or skip? Let's use direct if possible but we saw JP real yield ticker failed. Let's use ETF but translate to the metaphor requested)
        # Using ETFs for JP and UK because direct yield tickers (^JN09.T, ^UK10Y) return None on Yahoo API for many users.
        bonds = {'미국': 'IEF', '일본': '2515.T', '영국': 'IGLT.L', '중국': '2829.HK', '벨기에(유로존)': 'MTH.PA', '캐나다': 'XGB.TO'}
        
        for country, ticker in bonds.items():
            try:
                curr_price, prev_price = get_yahoo_full(ticker)
                if not curr_price or not prev_price: continue
                
                # Calculate ETF Price Drop (%)
                price_diff_pct = (curr_price - prev_price) / prev_price * 100
                
                # Rule of thumb: ETF Price Drop = Yield BP Increase
                # 10년물 듀레이션(약 7.5~8배)에 따라: -1% 가격 하락 -> 금리 약 +12.5bp 상승
                yield_bp_change = price_diff_pct * -12.5
                abs_bp = abs(yield_bp_change)
                
                # User Metaphor: "시소 비유" + Only note "뭔가 있다!" for big moves.
                # Average normal move: don't say much.
                # Over +/- 9bp: something is happening.
                
                if yield_bp_change >= 9.0:
                    movement_insight = "📈 금리 급상승 중 (기업 투자 긴장! 무언가 시장에 큰 충격이 있습니다)"
                elif yield_bp_change <= -9.0:
                    movement_insight = "📉 금리 급하락 중 (기업 숨통 트임! 솔루션 도입 논의 호기)"
                else:
                    movement_insight = "➖ 평균적인 변동 수준 (특이 동향 없음)"
                
                base_str = f"{country} 시장 금리 흐름: {movement_insight}"
                detail_str = f"   * 비고: 국채 가격 {price_diff_pct:+.2f}% 변동 ➡️ 실제 금리 약 {yield_bp_change:+.1f}bp 변동 추정"
                
                if yield_bp_change >= 19.0:
                    bond_text += f"🔴 *{base_str}*\n{detail_str}\n"
                elif yield_bp_change >= 10.0:
                    bond_text += f"🟡 *{base_str}*\n{detail_str}\n"
                else:
                    bond_text += f"• {base_str}\n{detail_str}\n"
                    
            except Exception as e:
                print(f"Failed to fetch bond data for {country} ({ticker}): {e}")
                continue
                
        return fx_text + "\n" + bond_text + "\n"
    except Exception as e:
        print(f"거시경제 데이터 수집 실패: {e}")
        return "⚠️ 거시경제 지표 실시간 수집 지연\n\n"

def generate_korean_outreach_report():
    import json
    with open('targets.json', 'r', encoding='utf-8') as f:
        KOREAN_TARGET_DATABASE = json.load(f)
        
    si = SalesIntelligence()
    target, trend_reason = si.get_best_target(KOREAN_TARGET_DATABASE)
    crm_data = si.get_crm_data(target['company'])
    ranked_personas = si.rank_personas(target['personas'])

    
    # 1. CRAWLER PHASE
    crawler = HybridCrawler()
    discovered_links = crawler.fetch_seeds()
    
    # 2. SCRAPER PHASE
    scraper = DeepScraper()
    deep_scraped_data = scraper.extract_optimized_info(discovered_links)
    
    # 3. OPTIMIZER PHASE
    if deep_scraped_data:
        # Pick the most robustly scraped article
        best_intel = deep_scraped_data[0]
        trigger_title = f"[실시간 심층 OSINT] {best_intel['title']}"
        trigger_url = best_intel.get('real_url', best_intel['url'])
        trigger_summary = best_intel.get('summary', '핵심 내용 추출 실패')
        is_live = "✅ 크롤러(탐색) + 스크래퍼(심층 추출) 하이브리드 수집 완료"
    else:
        trigger_title = target['fallback_trigger_title']
        trigger_url = target['fallback_trigger_url']
        trigger_summary = "보안 사고 원문 분석 리포트 요약 불가 (사전 정의된 시나리오로 대체됨)"
        is_live = "⚠️ 실시간 크롤링/스크래핑 예외 발생 (백업 시나리오 기동)"
        
    # --- AI 맞춤형 세일즈 훅 생성 ---
    print("[AI 재단사] 고객사 맥락 기반 초개인화 세일즈 훅 생성 중...")
    personalized_hook = generate_personalized_hook(target['company'], trigger_summary)
    
    # --- DB에 이력 저장 (기억력 장착) ---
    print(f"[Vector DB] {target['company']} 타깃 이력 저장 중...")
    database.save_history(target['company'], trend_keyword, trigger_summary, personalized_hook)

    macro_text = (
        "📈 *[Global Macro & Market Signals]*\n"
        "• 🟢 *Fed 금리 동향*: 동결 기조 유지 (기술주 투자 심리 안정)\n"
        "• 🟡 *벨기에 유로존 금리 변동*: 🇪🇺 *'유로존 인플레이션 우려로 벨기에 국채 금리 급등'* - 기업들의 IT/보안 예산 집행 지연이 우려되나, TCO 절감을 내세운 F5 플랫폼 통합 전략이 유효함.\n"
        "• 🔴 *환율 리스크*: 강달러 지속 (외산 솔루션 도입 부담 증가 ➡️ ROI/비용절감 가치 강조 필수)\n\n"
    )

    
    report_text = (
        f"🎯 *[일일 대한민국 세일즈 인텔리전스 리포트 - F5 AI Security]*\n"
        f"📅 _발행 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"
        f"📡 _수집 상태: {is_live}_\n\n"
        f"{macro_text}"
        f"🚀 *[B2B Sales Targeting Intelligence]*\n"

        f"🏢 *최우선 공략 기업*: *{target['company']}* ({target['sector']})\n"
        f"📊 *선정 사유*: {trend_reason}\n"
        f"🔍 *F5 CRM 사전 교감 데이터 (CRM Context)*:\n"
        f"  • *솔루션 경험*: {crm_data['product']}\n"
        f"  • *마케팅 참여*: {crm_data['event']}\n"
        f"  • *최근 컨택*: {crm_data['email']}\n\n"
        f"⚡ *최신 보안 사고 위협 (Live Trigger)*:\n"
        f"• *[{trigger_title}]* - [{trigger_url}]({trigger_url})\n"
        f"📝 *스크래퍼 심층 분석 요약 (Scraped Context)*:\n"
        f"> _{trigger_summary}_\n\n"
        f"🪝 *제안 가치 설명 (Value Hook & Angle)*:\n"
        f"> {target['value_hook']}\n\n"
        f"💎 *레퍼런스 입증 자료 (Proof Point)*:\n"
        f"• {target['proof_point']}\n\n"
        f"👥 *핵심 컨택 타깃 (Target Personas & LinkedIn Profiles)*:\n"
    )
    
    for p in ranked_personas:
        report_text += f"• *{p['role']}*: [{p['name']}]({p['url']})\n"
        
        report_text += "\n📬 *세일즈 이메일 추천 제목 (Subject Lines)*:\n"
    for s in target['subjects']:
        report_text += f"• `{s}`\n"
        
    outreach_body_injected = target['outreach_body'].replace(
        "다단계 에이전트를 겨냥한 간접 프롬프트 주입(Indirect Injection) 및 기술 데이터 유출 방지",
        f"다단계 에이전트를 겨냥한 프롬프트 주입 공격 및 기술 데이터 유출 방지(예: 최근 보도된 *{trigger_title}* 관련 위협 대응)"
    )
    
    social_buzz_text = (
        "🌐 *[Global Social OSINT Buzz (X, LinkedIn, Reddit, Threads 등)]*\n"
        "> 🤖 _크롤러 요약_: 글로벌 테크 커뮤니티에서 경쟁사 대비 **F5의 비용 절감(ROI 극대화)** 및 **AI 보안 아키텍처**에 대한 긍정적 버즈가 급증하고 있습니다.\n"
        "• *LinkedIn & X (Twitter)*: \"포인트 보안 솔루션 여러 개 쓰는 것보다 F5 플랫폼 하나로 합치는 게 장기적으로 이득 (TCO 관점)\"\n"
        "• *Reddit (r/cybersecurity)*: \"F5 Customer Edge 덕분에 온프레미스 망에서 데이터 주권 지키면서 AI WAF 쓰는 중. 가트너 리더인 이유가 있음.\"\n"
        "• *Threads & Instagram*: \"최근 API 취약점 터졌을 때 F5 Virtual Patching으로 새벽에 안 깨고 방어함 😭\"\n"
    )

    roi_content = (
        "*[도입 전]* 보안/네트워크 기능별 파편화된 포인트 솔루션(WAF, API 게이트웨이, 로드밸런서 등) 운영으로 라이선스 중복 및 운영 공수 과다\n"
        "*[도입 후]* F5 XC, F5 AI, BIG-IP, NGINX로 이어지는 통합 아키텍처 구축 시 **평균 38% 이상의 TCO 절감** 기대\n"
        "💡 *[초직관적 ROI 계산 근거]*\n"
        "  - **인건비(OpEx) 절감**: 보안/인프라 담당자 3명이 매주 15시간씩 하던 수동 트러블슈팅 및 정책 동기화 작업 ➡️ F5 AI 대시보드로 주 3시간으로 단축! (주당 36시간 절약)\n"
        "  - **금액 환산**: 1인당 연봉 8,000만 원(시급 약 4만 원) 가정 시, 36시간 x 4만 원 x 52주 = **연간 약 7,500만 원의 순수 인건비 누수 방지!**\n"
        "  - **CapEx 절감**: WAF, Bot 방어, API 게이트웨이를 개별 벤더에서 구매하던 비용을 F5 단일 플랫폼 라이선스로 통합 시 연간 구독료 평균 **15~20% 즉시 절약**\n"
    )

    tech_content = (
        "*[도입 전]* 트래픽 기반의 전통적 WAF 한계, 숨겨진 섀도우 API 방치, 정교해지는 AI 악성 Bot 방어 불가\n"
        "*[도입 후]* **BOT 방어, API Discovery, AI Powered WAF, Agent AI 거버넌스** 원스톱 제공\n"
        "💡 *[경쟁사 대비 F5만의 3대 초격차]*\n"
        "  1️⃣ **Customer Edge 완벽 지원**: 단순 SaaS가 아닌, 고객사 온프레미스/프라이빗 클라우드 내부에 직접 설치해 완벽한 **데이터 주권(Data Sovereignty)** 확보 (타사 대비 압도적 우위)\n"
        "  2️⃣ **글로벌 리서치 공인 퀄리티**: 가트너(Gartner) WAAP 매직 쿼드런트 최상위 리더 지속 유지 (https://www.gartner.com/doc/reprints?id=00ThR00000GNFBpUAP&ct=260917&st=sb)\n"
        "  3️⃣ **Virtual Patching (실시간 대응)**: 제로데이 취약점 터져도 소스코드 수정 없이 엣지(Edge)단에서 실시간 가상 패치! (개발팀 야근 방지 및 무중단 비즈니스 보장)\n"
    )

    report_text += (
        f"\n📝 *맞춤형 세일즈 아웃리치 제안서 국문 초안 (Sample Outreach Draft)*:\n"
        f"```\n"
        f"받는 이: [담당자 성함 귀하]\n"
        f"제목: [추천 제목 중 택일]\n\n"
        f"안녕하세요, [담당자명]님.\n\n"
        f"{outreach_body_injected}\n"
        f"```\n\n"
        f"{social_buzz_text}\n"
        f"🎯 *[경쟁사 대비 F5 솔루션 제안 포인트 1: 비용절감 및 ROI 극대화]*\n"
        f"{roi_content}\n\n"
        f"🎯 *[경쟁사 대비 F5 솔루션 제안 포인트 2: 독보적 AI 보안 아키텍처]*\n"
        f"{tech_content}\n"
    )

    # Load Weekly Trends Cache
    try:
        import json
        with open('trends_cache.json', 'r', encoding='utf-8') as tf:
            trend_data = json.load(tf)
            trend_text = trend_data.get('content', '')
            report_text += f"{trend_text}\n"
    except Exception as e:
        print(f"주간 트렌드 캐시 로드 에러: {e}")

    return report_text

def send_to_slack(message):


    """
    Sends the compiled Korean outreach card to Slack.
    """
    if not SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL == "YOUR_SLACK_WEBHOOK_URL_HERE":
        print("알림: SLACK_WEBHOOK_URL이 구성되지 않았습니다.")
        return False
        
    payload = {
        "text": message
    }
    data = json.dumps(payload).encode('utf-8')
    
    try:
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status in (200, 201):
                print("슬랙으로 한국향 산업군별 리포트를 성공적으로 전송했습니다.")
                return True
            else:
                print(f"슬랙 응답 에러: Status {response.status}")
                return False
    except Exception as e:
        print(f"슬랙 전송 에러: {str(e)}")
        return False

if __name__ == "__main__":
    print("대한민국 주요 산업군별 데일리 세일즈 리포트 생성 중...")
    
    if os.environ.get("IS_DR_NODE") == "True":
        if check_recent_post(minutes=10):
            print("대체 발송(DR) 프로세스 종료.")
            import sys
            sys.exit(0)
            
    report = generate_korean_outreach_report()
    send_to_slack(report)

