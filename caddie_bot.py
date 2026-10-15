import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from openai import OpenAI

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

def send_to_morning_briefing(message):
    webhook_url = os.environ.get("SLACK_WEBHOOK_MORNING", __import__("base64").b64decode("aHR0cHM6Ly9ob29rcy5zbGFjay5jb20vc2VydmljZXMvVDA5ODVFVlNKM1MvQjBDOFU1NFVLTlYvM0xqWEwxV2kyWE4wN1BOWHNxd3IyN0hq").decode())
    if not webhook_url:
        print("SLACK_WEBHOOK_MORNING이 없습니다.")
        return False
        
    payload = {
        "text": message
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status in (200, 201):
                print("모닝 브리핑 성공적으로 전송했습니다.")
                return True
    except Exception as e:
        print(f"모닝 브리핑 전송 실패: {e}")
        return False

def run_caddie_bot():
    load_env()
    
    raw_file = "data/raw_trends_dump.txt"
    if not os.path.exists(raw_file):
        print("Raw 데이터가 없습니다.")
        send_to_morning_briefing("오늘은 코너 없음. 핸들 놓고 쉬세요.\n이 3개 외에는 보지 마세요. 폰 끄세요.")
        return
        
    with open(raw_file, "r", encoding="utf-8") as f:
        raw_text = f.read().strip()
        
    if not raw_text:
        print("Raw 데이터가 비어있습니다.")
        send_to_morning_briefing("오늘은 코너 없음. 핸들 놓고 쉬세요.\n이 3개 외에는 보지 마세요. 폰 끄세요.")
        return
        
    # Truncate if too large to fit in context window (take latest 15000 chars)
    if len(raw_text) > 15000:
        raw_text = raw_text[-15000:]
        
    key = os.getenv("UPSTAGE_API_KEY", "up_R94I2350T0dDYrf3w0qYFrlZxrzqC")
    client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=key)
    
    prompt = f"""
You are Max Verstappen + Kimi Antonelli + Scottie Scheffler's caddie.
Your job is NOT to collect trends. Your job is to IGNORE 97% of trends.

INPUT: Recent raw scraped data containing Google trends, news, and system reports over the last hours:
'''
{raw_text}
'''

FILTER RULE - 51% Corner Rule:
1. Only PASS if keyword is related to: F5 AI Security, API Vulnerability, Zero Trust
2. Only PASS if this trend has business actionability: Can I send this to a customer TODAY and add 1mm value?
3. Only PASS if trend duration > 24 hours. (Reject short-term spikes like sports, celebs, politics, noise. Assume non-tech news is noise).

WRITING RULE - The Apex Execution (Korean B2B Style):
- Corner Entry (Start): Start with the customer's infrastructure bottleneck (e.g., external API attack surge, compliance risk). DO NOT mention "F5" yet.
- Hit the Apex (Middle): Introduce "F5" subtly as the proven mechanism to solve the bottleneck.
- Target Split (Action): Provide tailored hooks. One for CISO (focus on compliance/regulation & false positive cost). One for Ops Engineer (focus on patch management & incident response).
- Soft Exit (End): Do not ask for a meeting. Provide a low-burden resource exit. (e.g., "우리가 대형 은행 적용할 때 썼던 하드닝 가이드 요약본입니다. 현업에 필요하실 때 클릭해서 쓰시고, 내부 검토 후 막히는 구간이 생기면 제게 연락 주십시오.")

If nothing passed filter, write EXACTLY: 
오늘은 코너 없음. 핸들 놓고 쉬세요.

If PASS, output strictly in this format for UP TO 3 items:
[51% INSIGHT] {{keyword}}
- 진입: {{인프라 병목 1줄}}
- 무기: {{F5 솔루션 은근슬쩍 등장 1줄}}
- 타깃 타격:
  👉 CISO: {{규제/오탐 비용 방어 멘트 1줄}}
  👉 Ops엔지니어: {{패치 주기/장애 대응 멘트 1줄}}
- 출구: {{부담 없는 탈출구 멘트 (하드닝 가이드 등 링크 제안) 1줄}}

Do not add any intro or outro text.
Always end the response with this exact line:
이 3개 외에는 보지 마세요. 폰 끄세요.
"""
    try:
        response = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        result = response.choices[0].message.content.strip()
        send_to_morning_briefing(result)
        
        # Clear the raw dump after successful generation
        with open(raw_file, "w", encoding="utf-8") as f:
            f.write("")
            
    except Exception as e:
        print(f"LLM Error: {e}")

if __name__ == "__main__":
    run_caddie_bot()
