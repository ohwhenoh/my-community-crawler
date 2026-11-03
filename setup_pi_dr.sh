#!/bin/bash

echo "=== 라즈베리파이 DR 노드 불사신 설정 ==="
echo "1. 시스템 재부팅 시 도커 엔진 자동 기동 설정 (systemd)"
sudo systemctl enable docker
sudo systemctl start docker

echo "--------------------------------------------------------"
echo "2. 도커 컴포즈 기반 워치타워(Watchtower) 백그라운드 기동"
echo "이 작업은 docker-compose.yml이 있는 디렉토리에서 실행해야 합니다."
sudo docker compose up -d

echo "--------------------------------------------------------"
echo "✅ 처방전 투여 완료."
echo "이제 전원 플러그가 뽑혔다 꽂혀도, 라즈베리파이 OS만 올라오면"
echo "도커 엔진이 기동되고 컴포즈 설정(unless-stopped)에 의해 컨테이너들이 스스로 부활합니다."
echo "코드 최신화는 내부의 Watchtower가 GHCR을 주시하며 자동으로 수행합니다."
