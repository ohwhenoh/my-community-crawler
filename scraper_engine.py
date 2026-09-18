import re

def scrape_with_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return f"Playwright 라이브러리가 아직 설치되지 않았습니다. (동적 스크래핑 대기 중)"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # 동적 렌더링 및 클라우드플레어 우회를 위한 네트워크 유휴 상태 대기
            page.goto(url, wait_until="networkidle", timeout=20000)
            
            # 본문 텍스트 추출 (스크립트, 스타일 태그 제외)
            content = page.evaluate('''() => {
                const scripts = document.querySelectorAll('script, style');
                scripts.forEach(s => s.remove());
                return document.body.innerText;
            }''')
            browser.close()
            
            # 공백 정리 후 앞부분 요약 리턴
            clean_content = re.sub(r'\s+', ' ', content).strip()
            return clean_content[:800] + "..." if clean_content else "추출된 본문이 없습니다."
    except Exception as e:
        return f"Playwright 스크래핑 실패: {str(e)}"
