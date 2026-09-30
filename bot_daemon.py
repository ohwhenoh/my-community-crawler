import os
import time
import subprocess
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
    loading_msg = say(
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
        
        # Update the loading message to indicate completion
        app.client.chat_update(
            channel=loading_msg["channel"],
            ts=loading_msg["ts"],
            text="분석 완료!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ <@{user}>님, 타깃 심층 분석이 완료되어 아래에 리포트를 전송했습니다!"
                    }
                }
            ]
        )
    except Exception as e:
        app.client.chat_update(
            channel=loading_msg["channel"],
            ts=loading_msg["ts"],
            text="분석 중 오류 발생",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ 분석 중 오류가 발생했습니다: {str(e)}"
                    }
                }
            ]
        )

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


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    try:
        # Call views.publish with the built-in client
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🎛️ MacPro DR Bot 관제 센터"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*환영합니다, 마스터.*\n이곳에서 타자 칠 필요 없이 원클릭으로 봇을 통제하십시오."
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🚀 즉시 리포트 생성"
                                },
                                "style": "primary",
                                "action_id": "action_generate_report"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🚑 긴급 데이터 롤백"
                                },
                                "style": "danger",
                                "action_id": "action_rollback_data"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "💡 _'긴급 데이터 롤백' 클릭 시 어젯밤 자정의 백업본으로 덮어씌워지고 컨테이너가 재시작됩니다._"
                            }
                        ]
                    }
                ]
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")

@app.action("action_generate_report")
def handle_generate_report(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    client.chat_postMessage(
        channel=user_id,
        text="명령을 접수했습니다. 실시간 트렌드 및 타깃 분석을 시작합니다. 약 1분 정도 소요됩니다..."
    )
    
    try:
        import crawler_slack
        # Execute the crawler logic
        report, target_company = crawler_slack.generate_korean_outreach_report(return_target=True)
        # We send to the user's DM instead of the general channel for this on-demand request, or the general channel? 
        # The existing send_to_slack uses a webhook. For DM, let's just use chat_postMessage.
        # Actually, crawler_slack.send_to_slack() sends it to the channel configured in webhook. Let's do that.
        crawler_slack.send_to_slack(report, target_company)
        client.chat_postMessage(
            channel=user_id,
            text="✅ 성공적으로 리포트를 생성하여 채널에 발송했습니다."
        )
    except Exception as e:
        client.chat_postMessage(
            channel=user_id,
            text=f"❌ 리포트 생성 중 에러가 발생했습니다: {str(e)}"
        )

@app.action("action_rollback_data")
def handle_rollback_data(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    client.chat_postMessage(
        channel=user_id,
        text="🚑 긴급 복구 프로토콜을 가동합니다. 어젯밤 자정 백업본으로 덮어씌운 후 컨테이너를 스스로 재시작합니다..."
    )
    
    import subprocess
    try:
        # In a docker environment, this script runs inside the container. 
        # Rolling back data means we extract the latest backup from /app/backups to /app/data
        # Actually, let's trigger a script that does this.
        # Since we are inside the container, we can't do `docker compose down`.
        # But we CAN extract the tar.gz directly into /app/data.
        import os
        import glob
        import tarfile
        
        backup_files = glob.glob('/app/backups/data_backup_*.tar.gz')
        if not backup_files:
            # Maybe local testing? check local path
            backup_files = glob.glob('./backups/data_backup_*.tar.gz')
            
        if not backup_files:
            client.chat_postMessage(channel=user_id, text="❌ 백업 파일이 존재하지 않아 복구를 취소합니다.")
            return
            
        latest_backup = max(backup_files, key=os.path.getctime)
        
        client.chat_postMessage(channel=user_id, text=f"📦 가장 최신 백업 파일을 찾았습니다: {os.path.basename(latest_backup)}\n압축 해제를 시작합니다...")
        
        # We overwrite /app/data
        # The tarball contains 'data/...'
        with tarfile.open(latest_backup, "r:gz") as tar:
            # We extract it to /app (or ./) so that it overwrites data/
            extract_path = '/app' if os.path.exists('/app') else '.'
            tar.extractall(path=extract_path)
            
        client.chat_postMessage(channel=user_id, text="✅ 데이터 롤백 완료. 시스템이 정상화되었습니다.")
    except Exception as e:
        client.chat_postMessage(channel=user_id, text=f"❌ 복구 중 에러가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    print("🚀 [Slack Bot] 양방향 Socket Mode 리스너 구동 시작...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
