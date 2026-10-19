import os
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openai import OpenAI

# 슬랙 앱 토큰 및 봇 토큰 로드
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    print("⚠️ [봇 대기 모드] SLACK_APP_TOKEN 또는 SLACK_BOT_TOKEN이 설정되지 않아 양방향 챗봇 기능을 시작할 수 없습니다.")
    while True:
        time.sleep(3600)

app = App(token=SLACK_BOT_TOKEN)

def run_health_check(say, user):
    say(f"<@{user}>님, 🏥 AI API Health Dashboard를 구동합니다. 잠시만 기다려주세요...")
    try:
        upstage_key = os.getenv("UPSTAGE_API_KEY", "")
        nvidia_key = os.getenv("NVIDIA_API_KEY", "")
        
        result_msg = "=========================================\n 🏥 *AI API Health & Latency Dashboard*\n=========================================\n\n"
        
        # 1. NVIDIA Test
        result_msg += "*[1] Testing NVIDIA NIM (Llama 3.2 11B)...*\n"
        start_time = time.time()
        try:
            client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key, timeout=6.0, max_retries=0)
            client.chat.completions.create(
                model="meta/llama-3.2-11b-vision-instruct",
                messages=[{"role": "user", "content": "Ping"}],
                max_tokens=10
            )
            latency = time.time() - start_time
            result_msg += f"> ✅ Status: `HEALTHY` | ⏱️ Latency: `{latency:.2f}s` | Noisy Neighbor: SAFE\n\n"
        except Exception as e:
            latency = time.time() - start_time
            result_msg += f"> ❌ Status: `UNHEALTHY` | ⏱️ Latency: `{latency:.2f}s` | Error: `{str(e)[:50]}...`\n\n"

        # 2. Upstage Test
        result_msg += "*[2] Testing Upstage (Solar Mini)...*\n"
        start_time = time.time()
        try:
            client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=upstage_key, timeout=10.0, max_retries=0)
            client.chat.completions.create(
                model="solar-1-mini-chat",
                messages=[{"role": "user", "content": "Ping"}],
                max_tokens=10
            )
            latency = time.time() - start_time
            result_msg += f"> ✅ Status: `HEALTHY` | ⏱️ Latency: `{latency:.2f}s`\n"
        except Exception as e:
            latency = time.time() - start_time
            result_msg += f"> ❌ Status: `UNHEALTHY` | ⏱️ Latency: `{latency:.2f}s` | Error: `{str(e)[:50]}...`\n"
        
        say(result_msg)
    except Exception as e:
        say(f"❌ 헬스체크 중 오류가 발생했습니다: {str(e)}")

def run_target_analysis(say, user):
    say(
        text=f"<@{user}>님, 명령을 수신했습니다. 타깃을 심층 분석하여 즉시 리포트를 생성하겠습니다! ⏳ (약 10초 소요)",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<@{user}>님, 타깃 심층 분석을 시작합니다... 🏃‍♂️💨\n\n🔍 *[1/3] 웹 크롤링 엔진 가동 중...*\n🧠 *[2/3] AI 분석 및 세일즈 훅 생성 중...*\n\n_(잠시만 기다려주세요! 백그라운드에서 열심히 데이터를 수집하고 있습니다 📊)_"
                },
                "accessory": {
                    "type": "image",
                    "image_url": "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif",
                    "alt_text": "loading_spinner"
                }
            }
        ]
    )
    try:
        import crawler_slack
        report, target_company = crawler_slack.generate_korean_outreach_report(return_target=True)
        crawler_slack.send_to_slack(report, target_company)
    except Exception as e:
        say(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")

def chat_with_llm(say, user, text):
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")
    upstage_key = os.getenv("UPSTAGE_API_KEY", "")
    
    if not nvidia_key and not upstage_key:
        say(f"<@{user}>님, 죄송합니다. AI 키가 없어 일반 대화가 불가능합니다.")
        return
        
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key, timeout=15.0, max_retries=1)
        response = client.chat.completions.create(
            model="meta/llama-3.2-11b-vision-instruct",
            messages=[
                {"role": "system", "content": "당신은 F5 네트워크 보안 세일즈를 돕는 똑똑한 AI 비서 'MacPro DR Bot'입니다. 사용자의 질문에 자연스럽고 친절하게 한국어로 대답해주세요. 만약 시스템 상태나 헬스를 물어보면 '상태조회' 명령어를, 세일즈 리포트를 원하면 '타깃분석' 명령어를 타이핑해 달라고 안내해 주세요."},
                {"role": "user", "content": text}
            ],
            max_tokens=800
        )
        reply = response.choices[0].message.content
        say(f"<@{user}>님\n{reply}")
    except Exception as e:
        try:
            client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=upstage_key, timeout=15.0, max_retries=1)
            response = client.chat.completions.create(
                model="solar-1-mini-chat",
                messages=[
                    {"role": "system", "content": "당신은 F5 네트워크 보안 세일즈를 돕는 똑똑한 AI 비서 'MacPro DR Bot'입니다. 사용자의 질문에 자연스럽고 친절하게 한국어로 대답해주세요. 만약 시스템 상태나 헬스를 물어보면 '상태조회' 명령어를, 세일즈 리포트를 원하면 '타깃분석' 명령어를 타이핑해 달라고 안내해 주세요."},
                    {"role": "user", "content": text}
                ],
                max_tokens=800
            )
            reply = response.choices[0].message.content
            say(f"<@{user}>님\n{reply}")
        except Exception as e2:
            say(f"<@{user}>님, 죄송합니다. 지금은 AI 두뇌에 과부하가 발생했습니다. 나중에 다시 시도해주세요.")

@app.event("app_mention")

def handle_app_mention_events(body, say):
    print(f"🔔 [Event Received] app_mention: {body.get('event', {}).get('text')}")
    event = body.get("event", {})
    text = event.get("text", "")
    user = event.get("user")
    
    if "상태조회" in text:
        run_health_check(say, user)
    elif "타깃분석" in text or "타깃 분석" in text:
        run_target_analysis(say, user)
    else:
        chat_with_llm(say, user, text)

@app.event("message")
def handle_message_events(body, say):
    print(f"📩 [Message Received] type: {body.get('event', {}).get('channel_type')}, text: {body.get('event', {}).get('text')}")
    event = body.get("event", {})
    text = event.get("text", "")
    user = event.get("user")
    channel_type = event.get("channel_type")
    
    if channel_type == "im":
        if "상태조회" in text:
            run_health_check(say, user)
        elif "타깃분석" in text or "타깃 분석" in text:
            run_target_analysis(say, user)
        else:
            chat_with_llm(say, user, text)

if __name__ == "__main__":
    print("🚀 [Slack Bot] 양방향 Socket Mode 리스너 구동 시작...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
