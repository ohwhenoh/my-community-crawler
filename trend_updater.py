import requests
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from collections import Counter
import re
from datetime import datetime

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
        return f"글로벌 개발자 핫토픽: {', '.join(top)}"
    except:
        return "글로벌 개발자 핫토픽: API, LLM, Cloud"

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

def update_trends_cache():
    hn_buzz = get_hacker_news()
    global_news = get_bing_news("API security OR Web Application Firewall")
    kr_news = get_bing_news("제로트러스트 OR 망분리 OR 디도스 방어")
    
    content = f"""
🌟 *[주간 F5 세일즈 타겟팅 키워드 트렌드 (실시간 OSINT 갱신)]* 🌟
_(마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')})_

🌐 *[Global 트렌드 & F5 훅]*
1️⃣ *최신 보안 뉴스*: {global_news}
2️⃣ *해커뉴스 Buzz*: {hn_buzz}
💡 *F5 훅*: "글로벌에서 발생하는 최신 API/LLM 위협, F5 Distributed Cloud로 엣지에서 원천 차단하십시오."

🇰🇷 *[Korea 트렌드 & F5 훅]*
1️⃣ *국내 보안 이슈*: {kr_news}
2️⃣ *핵심 키워드*: 제로 트러스트, 데이터 주권, 지능형 DDoS
💡 *F5 훅*: "망분리 규제 완화와 제로 트러스트 전환, F5의 완벽한 온프레미스 지원(Customer Edge)으로 해결하십시오."
"""
    
    with open('trends_cache.json', 'w', encoding='utf-8') as f:
        json.dump({"updated_at": datetime.now().strftime('%Y-%m-%d'), "content": content}, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 트렌드 캐시 업데이트 완료.")

if __name__ == "__main__":
    update_trends_cache()
