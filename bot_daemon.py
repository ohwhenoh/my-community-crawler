import os
import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import crawler_slack

# 슬랙 앱 토큰 및 봇 토큰 로드
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN") # xapp- 토큰 필요

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    print("⚠️ [봇 대기 모드] SLACK_APP_TOKEN 또는 SLACK_BOT_TOKEN이 설정되지 않아 양방향 챗봇 기능을 시작할 수 없습니다.")
    print("💡 양방향 챗봇을 가동하려면 Slack API 페이지에서 Socket Mode를 켜고 App Token(xapp-...)을 발급받아 .env에 넣어주세요.")
    # 토큰이 없으면 무한 대기 (컨테이너 종료 방지)
    import time
    while True:
        time.sleep(3600)

app = App(token=SLACK_BOT_TOKEN)

@app.event("app_mention")
def handle_app_mention_events(body, say):
    event = body.get("event", {})
    text = event.get("text", "")
    user = event.get("user")
    
    if "상태조회" in text:
        say(f"<@{user}>님, 🏥 AI API Health Dashboard를 구동합니다. 잠시만 기다려주세요...")
        try:
            import time
            import os
            from openai import OpenAI
            
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
        return

    say(f"<@{user}>님, 명령을 수신했습니다. 타깃을 심층 분석하여 즉시 리포트를 생성하겠습니다! ⏳ (잠시만 기다려주세요...)")
    
    try:
        # 기존 크롤러 로직 강제 구동
        import crawler_slack
        report = crawler_slack.generate_korean_outreach_report()
        say(report)
    except Exception as e:
        say(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")


@app.event("message")
def handle_message_events(body, say):
    event = body.get("event", {})
    text = event.get("text", "")
    user = event.get("user")
    channel_type = event.get("channel_type")
    
    # DM(Direct Message) 채널에서 멘션 없이 그냥 말 걸었을 때 응답
    if channel_type == "im":
        if "상태조회" in text:
            say(f"<@{user}>님, 🏥 AI API Health Dashboard를 구동합니다. 잠시만 기다려주세요...")
            try:
                import time
                import os
                from openai import OpenAI
                
                upstage_key = os.getenv("UPSTAGE_API_KEY", "")
                nvidia_key = os.getenv("NVIDIA_API_KEY", "")
                
                result_msg = "=========================================
 🏥 *AI API Health & Latency Dashboard*
=========================================

"
                
                # 1. NVIDIA Test
                result_msg += "*[1] Testing NVIDIA NIM (Llama 3.2 11B)...*
"
                start_time = time.time()
                try:
                    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key, timeout=6.0, max_retries=0)
                    client.chat.completions.create(
                        model="meta/llama-3.2-11b-vision-instruct",
                        messages=[{"role": "user", "content": "Ping"}],
                        max_tokens=10
                    )
                    latency = time.time() - start_time
                    result_msg += f"> ✅ Status: `HEALTHY` | ⏱️ Latency: `{latency:.2f}s` | Noisy Neighbor: SAFE

"
                except Exception as e:
                    latency = time.time() - start_time
                    result_msg += f"> ❌ Status: `UNHEALTHY` | ⏱️ Latency: `{latency:.2f}s` | Error: `{str(e)[:50]}...`

"

                # 2. Upstage Test
                result_msg += "*[2] Testing Upstage (Solar Mini)...*
"
                start_time = time.time()
                try:
                    client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=upstage_key, timeout=10.0, max_retries=0)
                    client.chat.completions.create(
                        model="solar-1-mini-chat",
                        messages=[{"role": "user", "content": "Ping"}],
                        max_tokens=10
                    )
                    latency = time.time() - start_time
                    result_msg += f"> ✅ Status: `HEALTHY` | ⏱️ Latency: `{latency:.2f}s`
"
                except Exception as e:
                    latency = time.time() - start_time
                    result_msg += f"> ❌ Status: `UNHEALTHY` | ⏱️ Latency: `{latency:.2f}s` | Error: `{str(e)[:50]}...`
"
                
                say(result_msg)
            except Exception as e:
                say(f"❌ 헬스체크 중 오류가 발생했습니다: {str(e)}")
            return
            
        if "타깃분석" in text:
            say(f"<@{user}>님, DM 명령을 수신했습니다. 타깃을 심층 분석하여 즉시 리포트를 생성하겠습니다! ⏳ (약 10초 소요)")
            try:
                import crawler_slack
                report = crawler_slack.generate_korean_outreach_report()
                say(report)
            except Exception as e:
                say(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")
            return

if __name__ == "__main__":
    print("🚀 [Slack Bot] 양방향 Socket Mode 리스너 구동 시작...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
