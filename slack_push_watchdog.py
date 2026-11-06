#!/usr/bin/env python3
"""
슬랙 푸시 감시 스크립트 (자동 복구).
에러는 생긴다. 이를 인지하고 자동으로 다시 실행하는 것이 포인트다.
- 상태 파일(data/last_push_status.json)을 읽어 마지막 정기 푸시가 성공했는지 확인한다.
- 정기 푸시 시간(07:20, 10:50, 15:00 싱가포르 시간)이 지나고 20분이 됐는데도 성공한 푸시가 없으면 푸셔를 다시 실행한다.
- 라즈베리에서는 스케줄러 컨테이너가 살아 있는지 확인하고, 멈췄으면 다시 시작한다.
사용법: 크론에 15분마다 등록한다.
  */15 * * * * cd /home/oz/my-community-crawler && /usr/bin/python3 slack_push_watchdog.py >> logs/watchdog.log 2>&1
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(REPO_DIR, "data", "last_push_status.json")
LOG_FILE = os.path.join(REPO_DIR, "logs", "watchdog.log")
# 정기 푸시 시간 (싱가포르 시간)
SLOTS = ["07:20", "10:50", "15:00"]
GRACE_MINUTES = 20
COOLDOWN_MINUTES = 15
# 라즈베리 스케줄러 컨테이너 이름 (없으면 건너뛴다)
SCHEDULER_CONTAINER = "task_board_scheduler"


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [watchdog] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def read_status():
    try:
        with open(STATUS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def last_slot_before(now):
    # 지금보다 앞에 있는 가장 최근 정기 푸시 시간을 돌려준다. 없으면 None.
    today = now.strftime("%Y-%m-%d")
    best = None
    for s in SLOTS:
        slot = datetime.strptime(f"{today} {s}", "%Y-%m-%d %H:%M")
        if slot <= now and (best is None or slot > best):
            best = slot
    return best


def run_pusher():
    # 푸셔를 다시 실행한다. .env를 읽어 푸시 모드를 그대로 쓴다.
    log("푸셔를 다시 실행한다.")
    env = dict(os.environ)
    env_path = os.path.join(REPO_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(REPO_DIR, "slack_pusher.py")],
            cwd=REPO_DIR, env=env, capture_output=True, text=True, timeout=600,
        )
        tail = (r.stdout or "")[-500:]
        log(f"푸셔 다시 실행 완료 (종료 코드 {r.returncode}). 출력 꼬리: {tail!r}")
        return r.returncode == 0
    except Exception as e:
        log(f"푸셔 다시 실행 실패: {e}")
        return False


def check_container():
    # 라즈베리 스케줄러 컨테이너가 살아 있는지 확인하고, 멈췄으면 다시 시작한다.
    try:
        r = subprocess.run(
            ["docker", "ps", "--filter", f"name={SCHEDULER_CONTAINER}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=30,
        )
        if SCHEDULER_CONTAINER in (r.stdout or ""):
            return
        log(f"스케줄러 컨테이너({SCHEDULER_CONTAINER})가 안 보인다. 다시 시작한다.")
        r2 = subprocess.run(
            ["docker", "start", SCHEDULER_CONTAINER],
            capture_output=True, text=True, timeout=60,
        )
        log(f"컨테이너 다시 시작 결과: {r2.stdout.strip()} {r2.stderr.strip()}")
    except FileNotFoundError:
        # 도커가 없는 호스트(랙스다)에서는 건너뛴다.
        return
    except Exception as e:
        log(f"컨테이너 확인 실패: {e}")


def main():
    now = datetime.now()
    check_container()

    status = read_status()
    slot = last_slot_before(now)
    if slot is None:
        log("오늘 아직 정기 푸시 시간이 안 됐다. 할 일 없음.")
        return 0
    if now < slot + timedelta(minutes=GRACE_MINUTES):
        log(f"가장 최근 정기 푸시 {slot.strftime('%H:%M')}에서 {GRACE_MINUTES}분이 안 지났다. 할 일 없음.")
        return 0

    # 마지막 성공 푸시가 이 슬롯 이후인지 확인한다.
    last_ok = None
    last_attempt = None
    if status:
        try:
            last_attempt = datetime.strptime(status.get("time", ""), "%Y-%m-%d %H:%M:%S")
        except Exception:
            last_attempt = None
        if status.get("ok"):
            last_ok = last_attempt

    if last_ok and last_ok >= slot:
        log(f"정기 푸시 {slot.strftime('%H:%M')}는 이미 성공했다 (마지막 성공 {status.get('time')}). 할 일 없음.")
        return 0

    # 실패했거나 안 했으면, 마지막 시도가 얼마 안 됐으면 잠시 기다린다.
    if last_attempt and (now - last_attempt) < timedelta(minutes=COOLDOWN_MINUTES):
        log(f"마지막 시도 {status.get('time')}에서 {COOLDOWN_MINUTES}분이 안 지났다. 다음 감시 때 다시 확인한다.")
        return 0

    log(f"정기 푸시 {slot.strftime('%H:%M')}가 성공하지 않았다. 마지막 상태: {status}. 자동 복구로 푸셔를 다시 실행한다.")
    run_pusher()
    return 0


if __name__ == "__main__":
    sys.exit(main())
