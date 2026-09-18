#!/bin/bash

# ==============================================================================
# macOS Clamshell Mode (Lid Closed) Sleep Prevention Setup Script
# Keeps the Mac Pro awake when the lid is closed, ONLY when connected to AC power.
# ==============================================================================

echo "=== macOS Power Management Optimization ==="

# Check if pmset is available
if ! command -v pmset &> /dev/null; then
    echo "에러: pmset 명령어를 찾을 수 없습니다."
    exit 1
fi

echo "1. 충전기(AC Power) 연결 시 잠자기 비활성화 설정을 적용합니다."
echo "   (비밀번호를 요청하는 경우, Mac 로그인 비밀번호를 입력해 주십시오.)"
echo "   명령어: sudo pmset -c disablesleep 1"
echo "--------------------------------------------------------"

# We output the instruction for them to run in their shell, or let them approve the sudo execution.
# To ensure zero-trust safety, we explain the command clearly.
sudo pmset -c disablesleep 1

if [ $? -eq 0 ]; then
    echo "--------------------------------------------------------"
    echo "성공: 충전기 연결 시 화면을 덮어도 시스템이 대기(Sleep) 상태로 빠지지 않도록 정상 설정되었습니다."
else
    echo "--------------------------------------------------------"
    echo "경고: 권한 거부 또는 비밀번호 입력 취소로 인해 pmset 설정이 즉시 반영되지 않았습니다."
    echo "사용자 터미널에서 직접 'sudo pmset -c disablesleep 1'을 실행해 주십시오."
fi

echo ""
echo "2. 백그라운드 유휴 대기(Idle Sleep)를 방지하는 caffeinate 프로세스를 기동합니다."
# Run caffeinate in background preventing system idle and disk sleep
nohup caffeinate -s -i &> /dev/null &

echo "설정 작업이 완료되었습니다."
