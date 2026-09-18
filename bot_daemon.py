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
    
    say(f"<@{user}>님, 명령을 수신했습니다. 타깃을 심층 분석하여 즉시 리포트를 생성하겠습니다! ⏳ (잠시만 기다려주세요...)")
    
    try:
        # 기존 크롤러 로직 강제 구동
        report = crawler_slack.generate_korean_outreach_report()
        say(report)
    except Exception as e:
        say(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")

@app.message("타깃분석")
def message_hello(message, say):
    say("네! 타깃 분석을 원하시면 저를 멘션(@CrawlerBot)하고 명령해주세요!")

if __name__ == "__main__":
    print("🚀 [Slack Bot] 양방향 Socket Mode 리스너 구동 시작...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
