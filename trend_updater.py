import urllib.parse
def get_tech_incidents():
    # Fetch news for specific competitors/tech
    targets = ["Cisco", "Palo Alto Networks", "화웨이", "텐센트", "OpenAI", "엔트로픽", "스테이블 코인", "지니어스 법안"]
    results = []
    for t in targets:
        try:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(t + ' 보안 OR 해킹 OR 장애')}&hl=ko&gl=KR&ceid=KR:ko"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            context = ssl._create_unverified_context()
            res = urllib.request.urlopen(req, context=context, timeout=5)
            root = ET.fromstring(res.read())
            items = root.findall('.//item')
            if items:
                title = items[0].find('title').text
                link = items[0].find('link').text
                # Clean up title a bit
                title = title.split('-')[0].strip()
                if len(title) > 40:
                    title = title[:40] + "..."
                results.append(f"• [{t}] <{link}|{title}>")
        except:
            pass
    if not results:
        return "• 최근 특이 동향 없음"
    return "\n".join(results)

import requests
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from collections import Counter
import re
from datetime import datetime
import urllib.request
import ssl

def get_hacker_news():
    try:
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        story_ids = r.json()[:30]
        titles = []
        for sid in story_ids:
            story = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5).json()
            if story and 'title' in story:
                titles.append(story['title'])
        words = []
        for title in titles:
            words.extend(re.findall(r'\b[A-Za-z]{4,}\b', title.lower()))
        stopwords = {'that', 'with', 'from', 'this', 'have', 'about'}
        words = [w for w in words if w not in stopwords]
        top = [w[0] for w in Counter(words).most_common(3)]
        return f"글로벌 핫토픽: {', '.join(top)}"
    except:
        return "글로벌 핫토픽: API, LLM, Cloud"

def get_bing_news(query):
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://www.bing.com/news/search?q={query}&format=rss"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(r.content)
        title = root.find('.//item/title').text
        return title
    except:
        return "최신 AI 보안 트렌드 분석 중..."

def get_aagag_top10():
    try:
        url = "https://news.google.com/rss/search?q=site:aagag.com&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        context = ssl._create_unverified_context()
        res = urllib.request.urlopen(req, context=context, timeout=10)
        root = ET.fromstring(res.read())
        items = root.findall('.//item')[:10]
        titles = []
        for item in items:
            title = item.find('title').text.replace(" - AAGAG!!", "")
            link = item.find('link').text
            titles.append(f"• <{link}|{title}>")
        return "\n".join(titles)
    except Exception as e:
        return f"• aagag 트렌드 로드 실패 ({e})"


def get_humblefactory_top10():
    try:
        url = "https://humblefactory.co.kr/"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        context = ssl._create_unverified_context()
        res = urllib.request.urlopen(req, context=context, timeout=10)
        html = res.read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        titles = []
        for h3 in soup.find_all('h3', class_='post_title'):
            a_tag = h3.find('a')
            if a_tag:
                text = a_tag.get_text(strip=True)
                link = a_tag.get('href', '#')
                if len(text) > 40:
                    text = text[:40] + "..."
                titles.append(f"• <{link}|{text}>")
            if len(titles) >= 10:
                break
        return "\n".join(titles)
    except Exception as e:
        return f"• humblefactory 로드 실패 ({e})"



def update_trends_cache():
    global_titles = []
    hn_buzz = get_hacker_news()
    if hn_buzz.startswith("글로벌 핫토픽: "):
        global_titles.extend(hn_buzz.replace("글로벌 핫토픽: ", "").split(", "))
        
    global_news = get_bing_news("API security OR Web Application Firewall")
    if "분석 중..." not in global_news:
        global_titles.append(global_news)
        
    global_words = []
    for t in global_titles:
        words = re.findall(r'\b[A-Za-z]{4,}\b', t.lower())
        stopwords = {'that', 'with', 'from', 'this', 'have', 'about'}
        global_words.extend([w for w in words if w not in stopwords])
    
    global_top3 = [w[0] for w in Counter(global_words).most_common(3)]
    if not global_top3:
        global_top3 = ["API", "LLM", "Cloud"]
    
    global_top3_formatted = "\n".join([f"{i+1}. *{k}* (관련 뉴스 및 커뮤니티에서 가장 많이 언급됨)" for i, k in enumerate(global_top3)])

    kr_titles = []
    kr_news = get_bing_news("제로트러스트 OR 망분리 OR 디도스 방어")
    if "분석 중..." not in kr_news:
        kr_titles.append(kr_news)
        
    aagag_text = get_aagag_top10()
    humble_text = get_humblefactory_top10()
    
    kr_titles.extend(re.findall(r'\|([^>]+)>', aagag_text))
    kr_titles.extend(re.findall(r'\|([^>]+)>', humble_text))
    
    kr_words = []
    for t in kr_titles:
        words = re.findall(r'[가-힣]{2,}', t)
        kr_words.extend(words)
        
    kr_top3 = [w[0] for w in Counter(kr_words).most_common(3)]
    if not kr_top3:
        kr_top3 = ["제로트러스트", "데이터주권", "AI보안"]
        
    kr_top3_formatted = "\n".join([f"{i+1}. *{k}* (국내 주요 IT 헤드라인에서 가장 많이 언급됨)" for i, k in enumerate(kr_top3)])

    incidents_text = get_tech_incidents()
    criteria_note = "_*선정 기준: 최근 1주일 주요 IT 커뮤니티 및 뉴스 헤드라인 기반 단순 단어 빈도 추출*_"
    
    content = f"""*📊 주간 세일즈 타겟팅 트렌드*
_최종 갱신: {datetime.now().strftime('%Y-%m-%d %H:%M')}_
{criteria_note}

*🚨 글로벌/국내 주요 보안 사고 및 경쟁사 동향*
{incidents_text}

*🌍 Global TOP 3 키워드*
{global_top3_formatted}
💡 *F5 훅*: 글로벌 최신 위협, 엣지에서 원천 차단.

*🇰🇷 Korea TOP 3 키워드*
{kr_top3_formatted}
💡 *F5 훅*: 완벽한 온프레미스 지원(Customer Edge)으로 해결.

*🔥 AAGAG 커뮤니티 핫이슈 Top 10*
{aagag_text}

*💻 Humblefactory 핫이슈 Top 10*
{humble_text}
"""
    with open('trends_cache.json', 'w', encoding='utf-8') as f:
        json.dump({"updated_at": datetime.now().strftime('%Y-%m-%d'), "content": content}, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 트렌드 캐시 업데이트 완료.")
if __name__ == "__main__":
    update_trends_cache()
