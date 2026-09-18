# 🗂️ [INDEX] Python Flask Team Task Board Web Application System Guide
> **Search Keywords**: `python-flask`, `team-task-board`, `minimalist-card-layout`, `localhost-5001`, `macos-port-5000-conflict`, `airplay-receiver-fix`, `app.py`, `index.html`, `venv-setup`

---

## 📌 1. 시스템 정보 및 개요 (System Overview)
이 가이드는 로컬 환경에서 실행되는 초경량 단일 페이지 **Python Flask 기반 "팀 태스크 보드(Team Task Board)"**의 시스템 구조와 구동 절차를 담고 있습니다.

* **프로젝트 경로**: `/Users/o.choi/.gemini/antigravity/scratch/team-task-board`
* **개발 스택**: Python 3, Flask, Jinja2, HTML5, Vanilla CSS3 (Outfit Google Font)
* **네트워크 설정**: `127.0.0.1:5001` (포트 5001번)

---

## 🔑 2. 중요: macOS 포트 5000번 충돌 이슈 및 솔루션
기본 Flask 포트인 `5000`번은 **macOS 제어 센터의 'AirPlay 수신 모드(ControlCenter)'**가 선점하여 사용하고 있습니다. 
* **증상**: 브라우저에서 `127.0.0.1:5000` 접속 시 `HTTP 403 Forbidden` 에러 발생
* **해결**: 본 앱은 포트 충돌 우회를 위해 기본 구동 포트를 **`5001`**번으로 강제 고정해 두었습니다.

---

## 🚀 3. 초간단 1분 재구동 방법 (Quick Start Guide)
나중에 가상환경 폴더 없이 소스 코드만 보관된 상태에서 다시 앱을 띄우려면, 터미널에서 다음 5줄의 명령어만 실행하면 됩니다.

```bash
# 1) 프로젝트 폴더로 이동
cd /Users/o.choi/.gemini/antigravity/scratch/team-task-board

# 2) 가상환경(venv) 생성
python3 -m venv venv

# 3) 가상환경 활성화
source venv/bin/activate

# 4) Flask 패키지 설치
pip install flask

# 5) 서버 실행
python app.py
```

* **브라우저 접속 주소**: **`http://127.0.0.1:5001`**

---

## ⚙️ 4. 시스템 아키텍처 및 핵심 파일 설명 (Architecture)

### 🐍 1) Back-end: `app.py`
애플리케이션의 핵심 진입점으로 Flask 서버를 관리하며 Mock 데이터를 로드합니다.
* **Mock 데이터 구조**: 3개의 태스크 카드 정보
  1. `Update documentation homepage` (담당: Alex | 상태: In Progress)
  2. `Review security patch release` (담당: Jamie | 상태: Completed)
  3. `Draft Q3 product roadmap` (담당: Morgan | 상태: To Do)
* **포트 맵핑**: `app.run(host='127.0.0.1', port=5001, debug=True)`

### 🎨 2) Front-end: `templates/index.html`
미니멀한 카드 기반 레이아웃을 표현하는 단일 템플릿 파일입니다.
* **디자인 시스템 (CSS)**:
  - 밝은 회색 테마(`--bg-color: #f8fafc`)와 다크 슬레이트 텍스트(`--text-main: #0f172a`) 대비 적용
  - 마우스 롤오버 시 부드럽게 솟아오르는 인터랙션(Transition & Translate)과 은은한 글로우 섀도우 구현
  - To Do, In Progress, Completed 상태를 구분하는 색상 도트 및 저대비 고가독성 배지 구현
* **클라이언트 스크립트 (JS)**:
  - 각 카드의 "Mark as Complete" 버튼 클릭 시 `notifyUpdate()` 함수가 호출되어 브라우저 기본 Alert창(`Task updated!`)을 표시합니다.

---

## 🧹 5. 자원 정리 및 종료 방법 (Cleanup Guide)
* **서버 구동 종료**: 터미널 창에서 **`Ctrl + C`**를 누르면 즉시 웹 서버가 정지합니다.
* **가상환경 종료**: 터미널에 **`deactivate`**를 입력하면 가상환경 세션이 종료됩니다.
