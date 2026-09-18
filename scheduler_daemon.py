import time
import subprocess
import sys
from datetime import datetime

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
    
    if is_dr:
        print("🔧 [DR 모드] 라즈베리파이 백업 노드로 기동되었습니다. 정각 3분 뒤에 중복 검사를 시작합니다.", flush=True)
        trigger_times = ["08:43", "10:53", "15:33"]
    else:
        print("💻 [Primary 모드] 맥프로 메인 노드로 기동되었습니다.", flush=True)
        trigger_times = ["08:40", "10:50", "15:30"]

    last_trigger_date = ""
    
    try:
        while True:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            current_date_str = now.strftime("%Y-%m-%d")
            
            if current_time_str in trigger_times:
                trigger_key = f"{current_date_str}_{current_time_str}"
                if last_trigger_date != trigger_key:
                    run_scraper_job()
                    last_trigger_date = trigger_key
                    
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
