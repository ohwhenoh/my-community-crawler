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

def get_aagag_top5():
    try:
        # Use Google News RSS to bypass Cloudflare
        url = "https://news.google.com/rss/search?q=site:aagag.com&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        context = ssl._create_unverified_context()
        res = urllib.request.urlopen(req, context=context, timeout=10)
        root = ET.fromstring(res.read())
        items = root.findall('.//item')[:5]
        titles = []
        for item in items:
            title = item.find('title').text.replace(" - AAGAG!!", "")
            titles.append(f"• {title}")
        return "\n".join(titles)
    except Exception as e:
        return f"• aagag 트렌드 로드 실패 ({e})"

def get_humblefactory_top5():
    try:
        url = "https://humblefactory.co.kr/"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        context = ssl._create_unverified_context()
        res = urllib.request.urlopen(req, context=context, timeout=10)
        html = res.read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        titles = []
        # Find h3 elements with class post_title
        for h3 in soup.find_all('h3', class_='post_title'):
            a_tag = h3.find('a')
            if a_tag:
                text = a_tag.get_text(strip=True)
                # Shorten long titles for mobile readability
                if len(text) > 40:
                    text = text[:40] + "..."
                titles.append(f"• {text}")
            if len(titles) >= 5:
                break
        return "\n".join(titles)
    except Exception as e:
        return f"• humblefactory 로드 실패 ({e})"

def update_trends_cache():
    hn_buzz = get_hacker_news()
    global_news = get_bing_news("API security OR Web Application Firewall")
    kr_news = get_bing_news("제로트러스트 OR 망분리 OR 디도스 방어")
    
    aagag_text = get_aagag_top5()
    humble_text = get_humblefactory_top5()
    
    # Slack mobile optimized formatting
    content = f"""
[주간 세일즈 타겟팅 트렌드]
최종 갱신: {datetime.now().strftime('%Y-%m-%d %H:%M')}

[Global TOP 3 키워드]
1. 최신 보안 뉴스: {global_news}
2. 해커뉴스 Buzz: {hn_buzz}
💡 F5 훅: 글로벌 최신 위협, 엣지에서 원천 차단.

[Korea TOP 3 키워드]
1. 국내 보안 이슈: {kr_news}
2. 핵심 키워드: 제로 트러스트, 데이터 주권, 지능형 DDoS
💡 F5 훅: 완벽한 온프레미스 지원(Customer Edge)으로 해결.

[AAGAG 커뮤니티 핫이슈 Top 5]
{aagag_text}

[Humblefactory 핫이슈 Top 5]
{humble_text}
"""
    
    with open('trends_cache.json', 'w', encoding='utf-8') as f:
        json.dump({"updated_at": datetime.now().strftime('%Y-%m-%d'), "content": content}, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 트렌드 캐시 업데이트 완료.")

if __name__ == "__main__":
    update_trends_cache()
