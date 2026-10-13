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
    """
    Executes crawler_slack.py as a subprocess and logs output.
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 스케줄러: 실시간 OSINT 크롤러 기동 시작...", flush=True)
    try:
        # Run using python3
        res = subprocess.run(
            [sys.executable, "crawler_slack.py"],
            capture_output=True,
            text=True
        )
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 스케줄러: 크롤러 실행 완료 (Exit Code: {res.returncode})", flush=True)
        if res.stdout:
            print(f"--- 크롤러 출력 (STDOUT) ---\n{res.stdout.strip()}", flush=True)
        if res.stderr:
            print(f"--- 크롤러 오류 (STDERR) ---\n{res.stderr.strip()}", flush=True)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 스케줄러 실행 에러: {str(e)}", flush=True)




def run_caddie_bot_job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 챔피언 캐디 봇: 51% 필터링 모닝/오후 브리핑 기동...", flush=True)
    try:
        res = subprocess.run([sys.executable, "caddie_bot.py"], capture_output=True, text=True)
        if res.stdout:
            print(f"--- 캐디봇 STDOUT ---\n{res.stdout.strip()}", flush=True)
        if res.stderr:
            print(f"--- 캐디봇 STDERR ---\n{res.stderr.strip()}", flush=True)
    except Exception as e:
        print(f"캐디 봇 에러: {e}", flush=True)

def run_backup_job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 스케줄러: 일일 데이터 백업 기동 시작...", flush=True)
    try:
        backup_manager.run_backup_routine()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 백업 기동 에러: {str(e)}", flush=True)

def run_email_job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 스케줄러: 주간 이메일 발송 기동 시작...", flush=True)
    try:
        res = subprocess.run([sys.executable, "email_reporter.py"], capture_output=True, text=True)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 스케줄러: 주간 이메일 발송 완료 (Exit Code: {res.returncode})", flush=True)
        if res.stdout:
            print(f"--- 이메일 출력 (STDOUT) ---\n{res.stdout.strip()}", flush=True)
        if res.stderr:
            print(f"--- 이메일 오류 (STDERR) ---\n{res.stderr.strip()}", flush=True)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 이메일 발송 에러: {str(e)}", flush=True)

if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("🚀 대한민국 6대 산업군 실시간 OSINT 세일즈 스케줄러 데몬 시작", flush=True)
    print("⏱️  예약 타겟 시각: 매일 08:40, 10:50, 15:30 (하루 3회)", flush=True)
    print("=" * 60, flush=True)
    
    # Run an immediate dry-run to ensure docker container connectivity on startup
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 초기 기동 접속성 검증용 드라이런 대기...", flush=True)
    


    # DR Node starts 3 minutes later
    import os
    is_dr = os.environ.get("IS_DR_NODE") == "True"
    
    # Crawler runs periodically to feed the raw dump (e.g., every few hours)
    crawler_trigger_times = ["01:00", "05:00", "09:00", "13:00", "15:00", "19:00"]
    
    if is_dr:
        print("🔧 [DR 모드] 라즈베리파이 백업 노드로 기동되었습니다.", flush=True)
        # SGT 07:25, 16:00. DR node adds 3 minutes.
        caddie_trigger_times = ["07:28", "16:03"]
        email_trigger_time = "09:03"
        backup_trigger_time = "00:03"
    else:
        print("💻 [Primary 모드] 맥프로 메인 노드로 기동되었습니다.", flush=True)
        # SGT 07:25, 16:00
        caddie_trigger_times = ["07:25", "16:00"]
        email_trigger_time = "09:00"
        backup_trigger_time = "00:00"

    last_trigger_date = ""
    last_email_trigger_date = ""
    last_backup_date = ""
    
    try:
        while True:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            current_date_str = now.strftime("%Y-%m-%d")
            
            # 매주 금요일 이메일 발송 (now.weekday() == 4 is Friday)
            # 매일 자정 데이터 백업
            if current_time_str == backup_trigger_time:
                if last_backup_date != current_date_str:
                    run_backup_job()
                    last_backup_date = current_date_str

            if now.weekday() == 4 and current_time_str == email_trigger_time:
                email_trigger_key = f"{current_date_str}_{current_time_str}"
                if last_email_trigger_date != email_trigger_key:
                    run_email_job()
                    last_email_trigger_date = email_trigger_key

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
