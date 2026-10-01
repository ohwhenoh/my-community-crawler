import requests
from bs4 import BeautifulSoup
import os
from slack_sdk import WebClient

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")

def check_haerang():
    load_env()
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID")
    
    lock_file = "/tmp/haerang_alerted.lock"
    if os.path.exists(lock_file):
        print("해랑 12월 예약 알림이 이미 발송되었습니다. (락 파일 존재)")
        return

    url = "https://www.railcruise.co.kr/website/infault.asp"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        lines = text.split('\n')
        
        found = False
        target_text = ""
        for line in lines:
            # 정규식(Regex): '12월'과 '예약' 사이에 띄어쓰기가 몇 개든, 다른 글자(추가 상품 등)가 끼어있든 모두 잡아냅니다.
            # 예: 12월예약, 12월 예약, 12월 추가 상품 및 예약
            if re.search(r"12월.*?예약", line):
                found = True
                target_text = line
                break
                
        if found:
            client = WebClient(token=bot_token)
            message = f"🚨 *[해랑 열차 긴급 알림]* 🚨\n\n방금 홈페이지 공지사항에서 12월 예약 관련 텍스트가 감지되었습니다!\n발견된 텍스트: `{target_text}`\n\n🔗 접속하기: {url}"
            client.chat_postMessage(channel=channel_id, text=message)
            print("해랑 12월 예약 공지 감지! 슬랙 발송 완료.")
            
            with open(lock_file, "w") as f:
                f.write("alerted")
        else:
            print("해랑 12월 예약 공지 아직 없음.")
            
    except Exception as e:
        print(f"해랑 크롤링 실패: {e}")

if __name__ == "__main__":
    check_haerang()
