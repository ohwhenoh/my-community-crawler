import os
import time
import subprocess
import sys
import backup_manager
from datetime import datetime


def run_haerang_job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 해랑 열차 12월 예약 크롤링 기동...", flush=True)
    try:
        subprocess.run([sys.executable, "crawler_haerang.py"], check=False)
    except Exception as e:
        print(f"해랑 열차 크롤러 에러: {e}", flush=True)

def run_scraper_job():
    print("레거시 크롤러(crawler_slack.py)는 경량화 정책으로 인해 비활성화되었습니다.", flush=True)




# 푸시 담당 호스트만 True로 한다. 라즈베리파이(백업 노드)는 False로 둔다.
# 호스트마다 .env 파일에서 ENABLE_SLACK_PUSH 값을 다르게 준다.
ENABLE_SLACK_PUSH = os.environ.get("ENABLE_SLACK_PUSH", "false").lower() in ("1", "true", "yes")

def run_caddie_bot_job():
    if not ENABLE_SLACK_PUSH:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] slack_pusher 건너뜀: 이 호스트는 푸시 담당이 아닙니다 (ENABLE_SLACK_PUSH=false).", flush=True)
        return
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] slack_pusher (경량 B2B/트렌드) 기동...", flush=True)
    try:
        res = subprocess.run([sys.executable, "slack_pusher.py"], capture_output=True, text=True)
        if res.stdout:
            print(f"--- slack_pusher STDOUT ---\n{res.stdout.strip()}", flush=True)
        if res.stderr:
            print(f"--- slack_pusher STDERR ---\n{res.stderr.strip()}", flush=True)
    except Exception as e:
        print(f"slack_pusher 에러: {e}", flush=True)

def run_backup_job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 스케줄러: 일일 데이터 백업 기동 시작...", flush=True)
    try:
        backup_manager.run_backup_routine()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 백업 기동 에러: {str(e)}", flush=True)

if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("🚀 대한민국 6대 산업군 실시간 OSINT 세일즈 스케줄러 데몬 시작", flush=True)
    print("⏱️  푸시 시각: 매일 08:20, 11:50, 16:00 한국 시간 (하루 3회, 싱가포르 시간 07:20, 10:50, 15:00)", flush=True)
    print("=" * 60, flush=True)
    
    # Run an immediate dry-run to ensure docker container connectivity on startup
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 초기 기동 접속성 검증용 드라이런 대기...", flush=True)
    


    # DR Node starts 3 minutes later
    import os
    is_dr = os.environ.get("IS_DR_NODE") == "True"
    
    # Crawler runs periodically to feed the raw dump (e.g., every few hours)
    crawler_trigger_times = ["07:10", "16:00", "23:00"]
    
    if is_dr:
        print("🔧 [DR 모드] 라즈베리파이 백업 노드로 기동되었습니다.", flush=True)
        # 푸시 시각: 싱가포르 시간 07:20, 10:50, 15:00 -> 한국 시간 08:20, 11:50, 16:00.
        # 라즈베리는 기업 간 거래만, 랙스다는 소식만 보내므로 따로 늦추지 않는다.
        caddie_trigger_times = ["08:20", "11:50", "16:00"]
        backup_trigger_time = "00:03"
    else:
        print("💻 [Primary 모드] 맥프로 메인 노드로 기동되었습니다.", flush=True)
        # 푸시 시각: 싱가포르 시간 07:20, 10:50, 15:00 -> 한국 시간 08:20, 11:50, 16:00
        caddie_trigger_times = ["08:20", "11:50", "16:00"]
        backup_trigger_time = "00:00"

    last_trigger_date = ""
    last_backup_date = ""
    
    try:
        while True:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            current_date_str = now.strftime("%Y-%m-%d")
            
            # 매일 자정 데이터 백업
            if current_time_str == backup_trigger_time:
                if last_backup_date != current_date_str:
                    run_backup_job()
                    last_backup_date = current_date_str

            if current_time_str in crawler_trigger_times:
                trigger_key = f"{current_date_str}_{current_time_str}"
                if last_trigger_date != trigger_key:
                    run_scraper_job()
                    last_trigger_date = trigger_key

            if current_time_str in caddie_trigger_times:
                caddie_key = f"{current_date_str}_{current_time_str}"
                if getattr(sys, "last_caddie_date", "") != caddie_key:
                    run_caddie_bot_job()
                    sys.last_caddie_date = caddie_key
                    
            # Sleep for 10 seconds to check time precisely without consuming excessive CPU
            time.sleep(10)
    except KeyboardInterrupt:
        print("스케줄러가 종료되었습니다 (KeyboardInterrupt).", flush=True)
    except Exception as e:
        print(f"스케줄러 에러 발생: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        print("루프를 탈출하여 스크립트가 종료됩니다.", flush=True)
