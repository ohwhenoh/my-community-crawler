import os
import random
import requests
from bs4 import BeautifulSoup
import json
from openai import OpenAI

def get_korea_news():
    keywords = ["포티넷", "팔로알토네트웍스", "시스코", "클라우드 플레어", "아카마이", "A10 네트웍스", "AI", "SentinelOne", "Envoy", "Imperva", "Bot defense", "파이오링크", "라드웨어", "vmware", "nutanix", "minIO", "snowflake", "GPU", "데이터센터", "AI 보안", "사이버 보안", "클라우드 보안", "AI 기본법", "해킹", "KISA 보안공지", "재해복구", "DR"]
    
    # Pick 8 random keywords to increase volume
    selected_kws = random.sample(keywords, 8)
    articles = []
    
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    for kw in selected_kws:
        url = f"https://search.daum.net/search?w=news&q={kw}"
        try:
            r = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.select('div.item-title a')[:3]:
                title = a.text.strip()
                link = a.get('href', '')
                if title and link:
                    articles.append({"keyword": kw, "title": title, "link": link})
        except Exception as e:
            print(f"Scraping error for {kw}: {e}")
            
    if not articles:
        return ""
        
    prompt = f"""
You are a B2B IT Security Sales AI. 
I have scraped the following news articles from Korean portals today.
Please select all attention-grabbing, high-impact articles relevant to IT infrastructure, security, or our competitors. Do not artificially limit the number of articles; pick as many as are highly relevant.
OUTPUT EXACTLY A VALID JSON LIST OF OBJECTS with 'keyword', 'title' and 'link' keys. Do not include markdown blocks like ```json.
Ensure your JSON is perfectly valid. Do NOT use unicode escapes like \\uXXXX, use raw UTF-8 characters.
Articles:
{json.dumps(articles, ensure_ascii=False, indent=2)}

Format:
[
  {{"keyword": "keyword from input", "title": "article title", "link": "url"}}, ...
]
"""
    
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    upstage_key = os.getenv("UPSTAGE_API_KEY", "up_R94I2350T0dDYrf3w0qYFrlZxrzqC")
    
    result_text = ""
    # Try NVIDIA First
    try:
        if not nvidia_key: raise Exception("No NVIDIA Key")
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key, timeout=30.0, max_retries=2)
        resp = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        result_text = resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"NVIDIA API Failed: {e}. Falling back to Solar.")
        try:
            client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=upstage_key, timeout=30.0, max_retries=2)
            resp = client.chat.completions.create(
                model="solar-1-mini-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            result_text = resp.choices[0].message.content.strip()
        except Exception as e2:
            print(f"Solar API Failed: {e2}")
            return ""

    if result_text.startswith("```json"): result_text = result_text[7:]
    if result_text.startswith("```"): result_text = result_text[3:]
    if result_text.endswith("```"): result_text = result_text[:-3]
    result_text = result_text.strip()
    
    try:
        curated = json.loads(result_text)
    except json.JSONDecodeError as e:
        print(f"JSON Parse error: {e}. Attempting regex fallback.")
        import re
        import codecs
        curated = []
        pattern = re.compile(r'\{\s*"keyword"\s*:\s*"([^"]+)"\s*,\s*"title"\s*:\s*"([^"]+)"\s*,\s*"link"\s*:\s*"([^"]+)"\s*\}')
        for match in pattern.finditer(result_text):
            kw = match.group(1).encode('utf-8').decode('unicode_escape')
            title = match.group(2).encode('utf-8').decode('unicode_escape')
            link = match.group(3)
            curated.append({"keyword": kw, "title": title, "link": link})
        
    try:
        if not curated: return ""
        
        from collections import defaultdict
        grouped = defaultdict(list)
        for item in curated:
            kw = item.get("keyword", "트렌드")
            title = item.get("title", "").replace('\n', ' ')
            link = item.get("link", "")
            grouped[kw].append(f"• <{link}|{title}>")
            
        output = "\n\n*[오늘의 경쟁사 및 핫 트렌드 모니터링]*\n\n"
        for kw, articles in grouped.items():
            output += f"키워드: {kw}\n"
            for article in articles:
                output += f"{article}\n"
            output += "\n"
            
        return output.strip() + "\n"
    except Exception as e:
        print(f"JSON Parse error: {e}")
        return ""

if __name__ == "__main__":
    def load_env():
        env_path = ".env"
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip().strip("'\"")
    load_env()
    print(get_korea_news())
