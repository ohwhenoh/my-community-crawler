#!/bin/bash
echo "🚨 [긴급 복구] my-community-crawler 수동 힐링 스크립트 가동"

# 1. 도커 허브 오작동 유발하는 찌꺼기 설정 초기화
echo "{}" > ~/.docker/config.json
echo "✅ 도커 인증 설정 파일 초기화 완료"

# 2. 현재 실행 중인 과거 컨테이너 정리
docker compose down
echo "✅ 과거 컨테이너 종료 완료"

# 3. 명시적으로 ghcr.io 최신 이미지 Pull
echo "📥 깃허브 레지스트리(GHCR)에서 최신 이미지 강제 다운로드 중..."
docker compose pull

# 4. 재기동
docker compose up -d
echo "✅ 시스템 정상화 완료! 슬랙 관제 센터 대시보드를 확인하세요."
