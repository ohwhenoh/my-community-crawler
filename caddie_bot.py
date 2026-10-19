import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
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

def send_slack(message, webhook_url):
    if not webhook_url:
        print("Webhook URL이 없습니다.")
        return False
        
    payload = {"text": message}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status in (200, 201):
                return True
    except Exception as e:
        print(f"슬랙 전송 실패: {e}")
        return False

def run_caddie_bot():
    load_env()
    
    raw_file = "data/raw_trends_dump.txt"
    if not os.path.exists(raw_file):
        print("Raw 데이터 파일이 없습니다.")
        return
        
    with open(raw_file, "r", encoding="utf-8") as f:
        raw_text = f.read().strip()
        
    webhook_main = os.environ.get("SLACK_WEBHOOK_MORNING")
    if not webhook_main:
        webhook_main = __import__("base64").b64decode("aHR0cHM6Ly9ob29rcy5zbGFjay5jb20vc2VydmljZXMvVDA5ODVFVlNKM1MvQjBDOFU1NFVLTlYvM0xqWEwxV2kyWE4wN1BOWHNxd3IyN0hq").decode()
        
    webhook_raw = os.environ.get("SLACK_WEBHOOK_RAW")
    if not webhook_raw:
        webhook_raw = __import__("base64").b64decode("aHR0cHM6Ly9ob29rcy5zbGFjay5jb20vc2VydmljZXMvVDA5ODVFVlNKM1MvQjBDOFJVUUZZQ1MvS1JnU1RCdHA0YzAxUnFaQmRmeTFmZUU3").decode()
    
    if not raw_text:
        print("Raw 데이터가 비어있습니다. 오늘은 코너 없음.")
        send_slack("오늘은 코너 없음. 핸들 놓고 쉬세요.", webhook_main)
        return
        
    if len(raw_text) > 15000:
        raw_text = raw_text[-15000:]
        
    key = os.getenv("UPSTAGE_API_KEY", "up_R94I2350T0dDYrf3w0qYFrlZxrzqC")
    client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=key)
    
    prompt = f"""
You are an IT Security / Infrastructure trend analyzer for B2B sales.
Your job is to read the raw scraped news/trends and classify them into High-Impact APEX news and NOISE.
For APEX news, you will craft a compelling Slack message block based on the "Late Apex" and "Risk Transfer" strategy.

INPUT RAW DATA:
'''
{raw_text}
'''

FILTER RULE:
1. APEX NEWS: IT Security, API Vulnerability, AI threats, Zero Trust, infrastructure bottlenecks. Up to 3.
2. NOISE NEWS: General tech, sports, celebs, politics.

WRITING RULE FOR APEX NEWS (The "Late Apex" Strategy):
- 진입 (Entry): 
  DO NOT use any fear marketing (e.g. "오픈소스는 무조건 위험하다").
  State the objective, heavy FACT of the news clearly and coolly. 
  You MUST format the link EXACTLY using Slack's markdown: "<URL|객관적 팩트 요약>" (Do not print URL outside the brackets). 
  Format: "[출처, 날짜] <URL|객관적 팩트 요약>" (If no URL, just "[출처, 날짜] 객관적 팩트 요약")
- 지역화 (Localization) 우선순위:
  반드시 대한민국(South Korea)의 보안 사고, 공공/금융 규제, 기업 피해 사례를 최우선으로 탐색하여 맥락을 프레이밍하십시오. 국내 사례가 전혀 없을 경우에만 미국(US) 등 글로벌 사례로 넘어갑니다.
- 질문 (Question):
  Generate 2 separate sharp, factual, and CONCISE questions (under 15 words) hitting the core pain points:
  1) CISO/보안팀 대상: (Focus on legal/compliance/business risk, responsibility transfer, "선량한 관리자의 의무")
  2) 운영/개발/네트워크 엔지니어 대상: (Focus on operational fatigue, patch lead time, workload, "누가 멱살 잡히는가")
- 정적 (Silence):
  Provide a stark, dry realization connecting the fact to the operational burden, without begging or scaring.
  (e.g., "취약점이 발견되고 악용되는 속도는 수 시간 단위로 짧아졌는데, 패치의 책임과 부담은 여전히 운영팀이 고스란히 안고 있습니다.")
- 무기 (Weapon) - "Risk Transfer":
  1. 기사의 위협(Threat) 종류와 최신 보안 트렌드를 분석하여 가장 적합한 F5 솔루션을 유연하게 매핑하십시오. 
     (예시: NGINX Plus, F5 WAF, F5 WAAP, F5 API Security, F5 SSLO, F5 Distributed Cloud Bot Defense 등. 필요시 LLM의 지식을 바탕으로 예시에 없는 최적의 F5 솔루션이나 트렌드 키워드를 자율적으로 제시해도 무방합니다.)
  2. 제품의 기능 설명은 최소화하고, 방어를 벤더에게 이관하라는 논리를 전개하십시오.
  3. 반드시 아래의 '책임 전가' 맥락으로 무기 섹션을 마무리하십시오:
     "사고가 터졌을 때 사내에서 총알받이가 되지 마십시오. 벤더사(F5)의 상용 SLA와 VIP 방어 로직을 통해, CISO님과 보안팀이 '선량한 관리자의 의무'를 다했다는 가장 확실한 기술적/법적 방어막을 세워두십시오."

OUTPUT FORMAT:
Output ONLY a valid JSON object. No markdown, no code blocks.

{{
  "apex_news": [
    {{
      "keyword": "Short clear keyword",
      "entry": "[Source, Date] <URL|Heavy factual statement without fear mongering>",
      "ciso_question": "Sharp question for CISO",
      "ops_question": "Sharp question for Ops",
      "silence": "Stark realization about the operational burden",
      "weapon": "Mapped F5 solution + The Risk Transfer message (SLA, Duty of a good manager)"
    }}
  ],
  "noise_news": [
    "Noise news summary 1",
    "Noise news summary 2"
  ]
}}
"""
    
    kst_now = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{kst_now}] LLM 요청 시작...")
    
    try:
        response = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3
        )
        result = response.choices[0].message.content.strip()
        
        if result.startswith("```json"): result = result[7:]
        if result.startswith("```"): result = result[3:]
        if result.endswith("```"): result = result[:-3]
        result = result.strip()
        
        parsed = json.loads(result)
        
        apex_list = parsed.get("apex_news", [])
        noise_list = parsed.get("noise_news", [])
        
        main_messages = []
        
        manifesto = """*[Agent's Manifesto]*
에이펙스: (깊은 목소리로) "F5 OOO입니다. OOO 건 후속으로 짧게 통화 괜찮으십니까? 최근 OOO 관련 프론티어 AI 방어에 대한 이야기가 계속 나오는데, 다른 조직에서는 이 책임 소재 리스크에 어떻게 대응하시는지 공유 차원에서 메일 보내드렸습니다. 편하실 때 확인 부탁드립니다."
"""
        main_messages.append(manifesto)

        for item in apex_list:
            keyword = item.get("keyword", "")
            if not keyword: continue
            
            block = f"""[51% INSIGHT] {keyword}
- 진입: {item.get('entry', '')}

👉 CISO/보안팀: "{item.get('ciso_question', '')}"
👉 운영/엔지니어: "{item.get('ops_question', '')}"

{item.get('silence', '')}

- 무기: {item.get('weapon', '')}"""
            main_messages.append(block)
            
        if len(main_messages) > 1:
            final_main_msg = "\n\n========================\n\n".join(main_messages)
            send_slack(final_main_msg, webhook_main)
            print("메인 채널 전송 완료.")
        else:
            send_slack("오늘은 코너 없음. 핸들 놓고 쉬세요.", webhook_main)
            print("메인 채널 전송 완료 (코너 없음).")
            
        if noise_list:
            raw_msg = "*[f5-raw Noise Data]*\n" + "\n".join([f"- {n}" for n in noise_list])
            send_slack(raw_msg, webhook_raw)
            print("f5-raw 채널 전송 완료.")
            
        with open(raw_file, "w", encoding="utf-8") as f:
            f.write("")
            
    except Exception as e:
        print(f"LLM Error or JSON Parsing Failed: {e}")

if __name__ == "__main__":
    run_caddie_bot()
