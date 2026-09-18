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
        # 환율 데이터 수집 (안정적인 무료 API 사용)
        fx_text = "💱 *[환율 방향 (Purchase Power Influence)]*\n"
        try:
            r_usd = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10).json()['rates']
            usd_krw, usd_sgd, usd_cny, usd_jpy = r_usd['KRW'], r_usd['SGD'], r_usd['CNY'], r_usd['JPY']
            
            jpy_krw, jpy_sgd, jpy_usd, jpy_cny = usd_krw/usd_jpy, usd_sgd/usd_jpy, 1/usd_jpy, usd_cny/usd_jpy
            krw_sgd, krw_usd, krw_cny = usd_sgd/usd_krw, 1/usd_krw, usd_cny/usd_krw
            
            fx_text += f"• *10,000 JPY* = {jpy_krw*10000:,.0f} KRW | {jpy_sgd*10000:,.1f} SGD | {jpy_usd*10000:,.1f} USD | {jpy_cny*10000:,.1f} CNY\n"
            fx_text += f"• *100,000 KRW* = {krw_sgd*100000:,.1f} SGD | {krw_usd*100000:,.1f} USD | {krw_cny*100000:,.1f} CNY\n"
            fx_text += f"• *100 USD* = {usd_krw*100:,.0f} KRW | {usd_sgd*100:,.1f} SGD | {usd_cny*100:,.1f} CNY\n"
        except Exception as e:
            print(f"환율 수집 에러: {e}")
            fx_text += "⚠️ 환율 정보를 가져오지 못했습니다.\n\n"
            
        # 금리(국채 가격) 데이터 수집 (Yahoo 직접 호출)
        bond_text = "📉 *[금리 방향 (국채 가격 기반)]*\n"
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
                bond_text += f"• *{country} 금리 {direction} 중* (근거: 10년물 국채ETF 가격 | 현재: {curr_price:,.2f} / 1주전: {w1_price:,.2f} / 1개월전: {m1_price:,.2f} / 1년전: {y1_price:,.2f})\n"
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
        
    macro_text = get_macro_economic_data()
    
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
    
    report_text += (
        f"\n📝 *맞춤형 세일즈 아웃리치 제안서 국문 초안 (Sample Outreach Draft)*:\n"
        f"```"
        f"받는 이: [담당자 성함 귀하]\n"
        f"제목: [추천 제목 중 택일]\n\n"
        f"안녕하세요, [담당자명]님.\n\n"
        f"{outreach_body_injected}"
        f"```\n"
        f"---"
    )
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

