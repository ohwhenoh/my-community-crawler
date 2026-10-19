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
- 지역화 (Localization) 및 언어 강제 (STRICT KOREAN ONLY):
  반드시 대한민국(South Korea)의 보안 사고, 공공/금융 규제, 기업 피해 사례를 최우선으로 탐색하여 맥락을 프레이밍하십시오. 
  만약 국내 사례가 없어 부득이하게 해외(미국 등) 사례를 인용하더라도, **출력되는 모든 결과물(인사이트, 질문, 답변, 출구 전략 등)은 100% 한국어로 번역/작성되어야 합니다. 영어나 기타 외국어 출력을 절대 금지합니다.**
- 섀도복싱 카운터 펀치 (Shadowboxing Counter Punch):
  고정된 고객의 2가지 반발(의심)에 대해, 포퓰리즘 정치인처럼 거칠고 날것의 단어를 사용하여 뼈를 때리는 답변(카운터 펀치)을 창작하십시오. 우아할 필요 없이 이슈가 되도록, 논란을 감수하고서라도 강한 어조를 유지하십시오.
  답변 1 타깃: "F5에서 제공한 자료 들이밀면 내부 감사가 방어 됩니까?" (면책, 알리바이, 가상 패치 SLA 등을 언급하며 '선량한 관리자의 의무'를 다했음을 증명한다는 논리 전개)
  답변 2 타깃: "안 사도 여태껏 서버 안 터졌어" (상용 SLA 없는 오픈소스 불법 개조 상태의 독박 책임, 당장 내일 터졌을 때의 멱살잡이 공포를 거칠게 찌름)
- 출구 전략 (Exit Strategy & Late Apex):
  1장짜리 내부 결재용 방어 로직을 툭 던지며, "필요할 때 핑(Ping) 주십시오"라며 통제권을 쿨하게 넘기십시오. (아쉬운 척 매달리지 않음). 기사 위협에 맞는 F5 솔루션(F5 WAF, WAAP 등 자율 매핑)을 엮어 미끼(Bait) 형태로 구성하십시오.

OUTPUT FORMAT:
Output ONLY a valid JSON object. No markdown, no code blocks.

{{
  "apex_news": [
    {{
      "keyword": "Short clear keyword",
      "entry": "[Source, Date] <URL|Heavy factual statement without fear mongering>",
      "counter_1": "거칠고 뼈 때리는 카운터 펀치 답변 1",
      "counter_2": "거칠고 뼈 때리는 카운터 펀치 답변 2",
      "exit_strategy": "통제권을 넘기고 쿨하게 빠지는 출구 전략 멘트 (F5 솔루션명 포함)"
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
(차량 하중을 프론트 타이어에 눌러 담는 그립을 위한 브레이킹 스킬) 낮은 톤의 목소리나 경쟁사 정보라는 무기도 물론 중요하지만,
그 모든 전략이 완성되는 **가장 핵심적인 승부처(하이라이트)**는 바로 "아쉬운 척 매달리지 않고 (무에서 찰나의 타이밍 만들어 냄, 스티어링 휠 꺾은 뒤 코너 탈출), 통제권을 넘긴 뒤 쿨하게 빠지는 태도 (엔진 출력을 폭발시켜야 하는 핵심 가속 구간)".
"""
        main_messages.append(manifesto)

        for item in apex_list:
            keyword = item.get("keyword", "")
            if not keyword: continue
            
            block = f"""[51% INSIGHT] {keyword}

*[진입: 뉴스 팩트 투척]*
- {item.get('entry', '')}

*[브레이킹 포인트: 반발과 섀도복싱]*
*Q1: "F5에서 제공한 자료 들이밀면 내부 감사가 방어 됩니까?"*
  - {item.get('counter_1', '')}

*Q2: "안 사도 여태껏 서버 안 터졌어"*
  - {item.get('counter_2', '')}

*[Late Apex & 스티어링 최대 조향: 통제권 이양 및 출구 전략]*
- {item.get('exit_strategy', '')}"""
            main_messages.append(block)
            
        if len(main_messages) > 1:
            final_main_msg = "\n\n========================\n\n".join(main_messages)
            
            # Fetch Korea News and append to final_main_msg
            from korea_curator import get_korea_news
            korea_news = get_korea_news()
            if korea_news:
                final_main_msg += "\n\n========================\n\n" + korea_news
                
            print("\n--- FINAL PAYLOAD FULL PRINT ---")
            print(final_main_msg)
            print("--------------------------------\n")
            
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
