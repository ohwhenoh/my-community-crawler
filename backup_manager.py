import os
import time
import shutil
import tarfile
from datetime import datetime, timedelta

DATA_DIR = "./data"
BACKUP_DIR = "./backups"
RETENTION_DAYS = 7  # 1 week

def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    if not os.path.exists(DATA_DIR):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 백업 실패: {DATA_DIR} 디렉토리가 존재하지 않습니다.")
        return

    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"data_backup_{date_str}.tar.gz"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(DATA_DIR, arcname=os.path.basename(DATA_DIR))
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 백업 완료: {backup_path}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 백업 에러: {e}")

def cleanup_old_backups():
    if not os.path.exists(BACKUP_DIR):
        return
        
    now = time.time()
    for filename in os.listdir(BACKUP_DIR):
        filepath = os.path.join(BACKUP_DIR, filename)
        if os.path.isfile(filepath):
            file_age_days = (now - os.path.getmtime(filepath)) / (60 * 60 * 24)
            if file_age_days > RETENTION_DAYS:
                try:
                    os.remove(filepath)
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오래된 백업 삭제 완료 (6개월 경과): {filename}")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 백업 삭제 에러 ({filename}): {e}")

def run_backup_routine():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 백업 루틴 시작...")
    create_backup()
    cleanup_old_backups()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 백업 루틴 종료.")

if __name__ == "__main__":
    run_backup_routine()
