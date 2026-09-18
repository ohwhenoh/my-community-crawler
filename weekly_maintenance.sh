#!/bin/bash

# 로그 파일 경로 설정
LOG_FILE="/home/oz/my-community-crawler/maintenance.log"

echo "========================================" >> $LOG_FILE
echo "[$(date)] 🧹 주간 시스템 및 보안 최적화 시작" >> $LOG_FILE

echo "[1/4] Docker 캐시 및 미사용 볼륨 완전 삭제..." >> $LOG_FILE
# 실행 중이지 않은 모든 도커 이미지/볼륨/네트워크 삭제
docker system prune -af --volumes >> $LOG_FILE 2>&1

echo "[2/4] OS 보안 패치 업데이트 및 불필요한 패키지 청소..." >> $LOG_FILE
sudo apt-get update >> $LOG_FILE 2>&1
sudo apt-get upgrade -y >> $LOG_FILE 2>&1
sudo apt-get autoremove -y >> $LOG_FILE 2>&1
sudo apt-get clean >> $LOG_FILE 2>&1

echo "[3/4] 메모리(RAM) 누수 방지를 위한 캐시 드롭..." >> $LOG_FILE
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >> $LOG_FILE 2>&1

echo "[4/4] SD카드 수명 연장을 위한 Swap 최적화 적용..." >> $LOG_FILE
sudo sysctl vm.swappiness=10 >> $LOG_FILE 2>&1

echo "[$(date)] 🚀 주간 시스템 최적화 완료!" >> $LOG_FILE
echo "========================================" >> $LOG_FILE
