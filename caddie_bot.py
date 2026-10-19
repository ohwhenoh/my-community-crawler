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
- 심리적 후킹 및 맥락 (Hooking & Context):
  절대 "미팅할 시간 되나요?", "어떻게 대응하고 있나요?" 같은 고객의 뇌 연산 부하를 요구하는 질문(Heavy 쿼리)을 던지지 마십시오.
  대신, 기사의 위협과 관련하여 상용 SLA 보증이 없을 때 그 공백 기간 동안 사고가 발생하면 징계와 책임이 온전히 내부 인프라 및 보안 책임자에게 '독박'으로 쏠리게 되는 현실(규제 감사 타깃 등)을 건조하게 짚어주십시오.
  (예: "최근 오픈소스 취약점(CVE) 발표 직후 커뮤니티의 공식 패치가 배포되기 전까지 발생하는 '방어 공백' 기간이, 규제 기관 보안 감사의 핵심 타깃이 되고 있습니다. 상용 SLA 보증이 없는 오픈소스 인프라 특성상, 이 공백 기간 동안 사고가 발생할 경우 그 징계와 책임은 온전히 내부 인프라 및 보안 책임자에게 독박으로 쏠리게 됩니다.")
- 무기 및 출구 전략 (Weapon & Exit Strategy) - "Risk Transfer":
  미팅을 구걸하지 말고 "필요할 때 네가 호출해라"라며 통제권을 완전히 넘기십시오(Steering Wheel 이양). 
  외부 감사 시 '선량한 관리자의 주의 의무'를 다했음을 기술적으로 증명하고 책임을 외부로 전가할 수 있는 **'1장짜리 내부 결재용 방어 로직(알리바이)'**이나 '리스크 면책용 대응 레퍼런스'를 남겨둔다고 명시하며 쿨하게 이탈하십시오.
  위협(Threat)에 맞는 최적의 F5 솔루션(예: F5 WAF, F5 WAAP, F5 API Security, NGINX Plus 등 자율 매핑)을 유추하여 이 레퍼런스의 주체로 삼으십시오.
  (예: "외부 감사 시 '선량한 관리자의 주의 의무'를 다했음을 기술적으로 증명하고 책임을 외부로 전가할 수 있는, 동종 업계의 '오픈소스 리스크 면책용 대응 레퍼런스'를 남겨둡니다. 내부 검토 후 필요하실 때 핑 주십시오.")

OUTPUT FORMAT:
Output ONLY a valid JSON object. No markdown, no code blocks.

{{
  "apex_news": [
    {{
      "keyword": "Short clear keyword",
      "entry": "[Source, Date] <URL|Heavy factual statement without fear mongering>",
      "hooking_context": "Dry context about the risk of '독박' responsibility and regulatory audit target.",
      "exit_strategy": "Cool exit offering the 1-page defense logic/reference and handing over control (e.g. '필요할 때 핑 주십시오').",
      "f5_reference": "Mapped F5 solution name (e.g. F5 WAAP 방어 로직 레퍼런스)"
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

{item.get('hooking_context', '')}

{item.get('exit_strategy', '')}


- 무기: {item.get('f5_reference', '')}"""
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
