#!/usr/bin/env python3
"""
슬랙 푸셔 가드레일 헬퍼.
오늘(2026-11-06) 겪은 에러를 미리 막고, 고칠 수 있는 것은 자동으로 고친다.
사용법: python3 slack_pusher_guard.py [--check-only] [slack_pusher.py 경로]
종료 코드: 0 = 통과, 1 = 실패(고칠 수 없는 문제 남음)
--check-only: 자동 수정을 하지 않고 문제만 보고한다. 깃허브 빌드에서 쓴다.
"""
import json
import os
import re
import shutil
import sys

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slack_pusher.py")

# ---------- 1. 소스 정적 검사 ----------
def check_source(path):
    """slack_pusher.py 소스를 읽어 오늘의 에러 패턴이 있는지 검사한다. 문제 목록을 돌려준다."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    problems = []

    # (1) 검색 링크에 &가 있으면 슬랙 400번 오류. 오늘 첫 번째 400번 원인.
    # 주의: 가져오기 주소(url = ... rss/search...)의 &는 정상이다. 가져오기는 &가 필요하고,
    # 슬랙 링크(search_link)만 &가 없어야 한다. 둘을 구분한다.
    for _line in src.splitlines():
        if '"search_link"' in _line and "&" in _line:
            problems.append(("search_link_amp", "검색 링크(search_link)에 &가 있다. 슬랙 400번 오류 원인."))
            break

    # (2) 구역 나누기가 개수 기준이면 긴 제목이 3000자를 넘겨 400번 오류. 오늘 두 번째 400번 원인.
    if "chunk_size = 10" in src:
        problems.append(("chunk_by_count", "구역 나누기가 개수(10개) 기준이다. 긴 제목이 3000자를 넘겨 400번 오류가 난다."))
    if "_split_long_sections" not in src:
        problems.append(("no_section_guard", "자동 수정 가드레일 _split_long_sections이 없다."))
    if "_validate_payload" not in src:
        problems.append(("no_validate", "보내기 전 검사 _validate_payload가 없다."))
    if "_safe_mrkdwn_link" not in src:
        problems.append(("no_safe_link", "링크 주소 정리 _safe_mrkdwn_link가 없다."))

    # (3) 전송 실패 때 보낸 기록을 저장하면 실패한 기사가 안 온다. 오늘의 중복 방지 소실 원인.
    if "_sent_ok" not in src or "보낸 기록을 저장하지 않는다" not in src:
        problems.append(("no_history_guard", "전송 실패 때 보낸 기록을 저장하지 않는 가드레일이 없다."))

    # (4) Top 10이 낱말 빈도면 파트너님 구절이 안 나온다. 오늘 발견한 문제.
    top10_block = re.search(r"# 핵심 키워드 Top 10.*?top10_str = ", src, re.S)
    if top10_block and "TARGET_KEYWORDS" not in top10_block.group(0):
        problems.append(("top10_words", "Top 10이 감시 단어 구절이 아니라 낱말 빈도로 계산된다."))

    # (7) Top 10 계산에 검색량이 들어가면 한 건의 검색량이 순위를 지배한다. (2026-11-23)
    if top10_block and "_parse_traffic" in top10_block.group(0):
        problems.append(("top10_traffic_weight", "Top 10 계산에 검색량(_parse_traffic)이 들어간다. 건수만 세야 한다."))

    # (8) 보내기 전 내용 검사가 없으면 오늘 고친 오류가 다시 슬랙에 나간다. (2026-11-23)
    if '"검색량 미상"' not in src:
        problems.append(("no_content_check", "보내기 전 내용 검사에 '검색량 미상' 검사가 없다."))
    if "내용 검사 실패" not in src:
        problems.append(("no_validation_error_record", "내용 검사 실패가 상태 파일에 기록되지 않는다. 감시 스크립트가 실패를 알아챌 수 없다."))

    # (6) 자동 복구: 다시 시도와 상태 기록이 없으면 일시적 오류에 푸시가 그냥 죽는다.
    if "_fetch_with_retry" not in src or "_post_with_retry" not in src:
        problems.append(("no_retry", "다시 시도(_fetch_with_retry / _post_with_retry)가 없다. 일시적 오류에 푸시가 그냥 죽는다."))
    if "_write_push_status" not in src:
        problems.append(("no_status", "상태 파일 기록(_write_push_status)이 없다. 감시 스크립트가 실패를 알아챌 수 없다."))
    if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(path)), "slack_push_watchdog.py")):
        problems.append(("no_watchdog", "감시 스크립트 slack_push_watchdog.py가 없다. 실패한 정기 푸시를 자동으로 다시 실행할 수 없다."))

    return problems


def fix_source(path, problems):
    """고칠 수 있는 소스 문제를 자동으로 고친다. 바꾼 개수를 돌려준다."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    fixed = 0
    kinds = {p[0] for p in problems}

    if "search_link_amp" in kinds:
        # 검색 링크(search_link) 줄에서 &로 시작하는 추가 매개변수를 뗀다.
        # 가져오기 주소(url = ... rss/search...)는 건드리지 않는다. 가져오기는 &가 필요하다.
        new_src = re.sub(r'("search_link": "https://news\.google\.com/search\?q=" \+ _up\.quote\(keyword\))[^,\n]*', r'\1', src)
        if new_src != src:
            src = new_src
            fixed += 1

    if "chunk_by_count" in kinds:
        # 개수 기준 나누기 전체를 글자 수 기준 나누기로 바꾼다.
        old_loop = '''                chunk_size = 10  # 3000자 제한 방지
                for i in range(0, len(items), chunk_size):
                    chunk = items[i:i + chunk_size]
                    header_text = f"*{cat_name}*" if i == 0 else f"*{cat_name}* (계속)"
                    trends_blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": header_text + "\\n" + "\\n".join(chunk)}
                    })'''
        new_loop = '''                # 3000자 제한: 개수 기준이 아니라 글자 수 기준으로 나눈다. 긴 제목이 많으면 10개도 3000자를 넘는다.
                _chunks = []
                _cur = []
                _cur_len = 0
                for _it in items:
                    _it_len = len(_it) + 1
                    if _cur and _cur_len + _it_len > 2800:
                        _chunks.append(_cur)
                        _cur = []
                        _cur_len = 0
                    _cur.append(_it)
                    _cur_len += _it_len
                if _cur:
                    _chunks.append(_cur)
                for _ci, _chunk in enumerate(_chunks):
                    header_text = f"*{cat_name}*" if _ci == 0 else f"*{cat_name}* (계속)"
                    trends_blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": header_text + "\\n" + "\\n".join(_chunk)}
                    })'''
        if old_loop in src:
            src = src.replace(old_loop, new_loop, 1)
            fixed += 1
        else:
            # 루프 모양이 다르면 할당 줄만이라도 무해하게 바꾼다.
            new_src = src.replace("chunk_size = 10  # 3000자 제한 방지", "_char_limit = 2800  # 3000자 제한: 글자 수 기준")
            if new_src != src:
                src = new_src
                fixed += 1

    if fixed:
        bak = path + ".bak-guard-" + __import__("datetime").datetime.now().strftime("%Y%m%d%H%M%S")
        shutil.copy2(path, bak)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"자동 수정 {fixed}건 적용. 백업: {bak}")
    return fixed


# ---------- 2. 모의 실행(드라이런) 검사 ----------
def dry_run(path):
    """네트워크와 슬랙 발송을 가짜로 바꿔 send_slack을 돌리고, 만든 보고서를 검사한다."""
    # 모듈이 가져올 때 웹훅 주소를 읽으므로, 가져오기 전에 가짜 주소를 넣어둔다.
    os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/GUARD-TEST"
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    import importlib.util
    spec = importlib.util.spec_from_file_location("sp_guard_target", path)
    sp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sp)

    sent = []
    class R:
        status_code = 200
    sp.requests.post = lambda url, json=None, timeout=10: (sent.append(json), R())[1]
    sp.load_history = lambda: set()
    sp.save_history = lambda s: None
    # 기업 간 거래 보고서는 가짜로 바꾸지 않는다. 진짜 함수를 가짜 자료로 돌려 검사한다. (2026-11-23)
    # 가짜 트렌드: 감시 단어에 맞는 것 2개, 안 맞는 것 1개, 긴 제목 12개
    def fake_trends(geo, limit=5):
        out = [
            {"keyword": "미국 중간선거 개표", "traffic": "50000",
             "search_link": "https://www.google.com/search?q=x",
             "news": [{"title": "미국 중간선거 개표 시작", "url": "https://example.com/midterm"}],
             "geo_name": geo},
            {"keyword": "연예인 결혼", "traffic": "9000",
             "search_link": "https://www.google.com/search?q=x",
             "news": [{"title": "연예인 결혼 발표", "url": "https://example.com/wedding"}],
             "geo_name": geo},
        ]
        for i in range(12):
            out.append({"keyword": "엔비디아 긴제목" + str(i), "traffic": "1000",
                        "search_link": "https://www.google.com/search?q=x",
                        "news": [{"title": "엔비디아 " + "가" * 240 + " 제목 " + str(i),
                                  "url": "https://example.com/long" + str(i)}],
                        "geo_name": geo})
        return out
    sp.get_google_trends_raw = fake_trends
    def fake_kw(keyword, limit=5):
        return {"keyword": keyword, "traffic": "",
                "search_link": "https://news.google.com/search?q=" + keyword,
                "news": [{"title": keyword + " 관련 최신 소식",
                          "url": "https://news.google.com/rss/articles/KW-" + keyword,
                          "source": "한국경제"}],
                "geo_name": "South Korea"}
    sp.get_keyword_news = fake_kw

    problems = []
    os.environ["PUSH_MODE"] = "trends"
    sent.clear()
    sp.send_slack()
    if len(sent) != 1:
        problems.append(f"소식 모드에서 보고서 {len(sent)}개가 나왔다. 1개여야 한다.")
        return problems
    tr = sent[0]
    body = json.dumps(tr, ensure_ascii=False)
    if "연예인 결혼" in body.split("📈 구글 트렌드 24시간")[0]:
        problems.append("필터가 안 맞는 트렌드(연예인 결혼)가 주제에 들어갔다.")
    if "미국 중간선거" not in body:
        problems.append("맞는 트렌드(미국 중간선거)가 보고서에 없다.")
    missing = [k for k in sp.WATCH_KEYWORDS if k not in body]
    if missing:
        problems.append(f"감시 단어 {len(missing)}개가 보고서에 없다. 예: {missing[:3]}")
    blocks = tr.get("blocks", [])
    if len(blocks) > 50:
        problems.append(f"블록 {len(blocks)}개가 50개 제한을 넘는다.")
    for b in blocks:
        if b.get("type") == "section":
            t = b["text"]["text"]
            if len(t) > 3000:
                problems.append(f"구역 {len(t)}자가 3000자 제한을 넘는다. 자동 수정이 안 됐다.")
            for u in re.findall(r"<(https?://[^>|]+)", t):
                if "&" in u:
                    problems.append(f"링크 주소에 &가 있다: {u[:80]}")
    # Top 10은 감시 단어 구절이어야 한다
    top = ""
    for b in blocks:
        if b.get("type") == "context":
            top = b["elements"][0]["text"]
    if "Top 10" not in top:
        problems.append("Top 10이 없다.")
    else:
        tail = top.split("Top 10*:", 1)[1]
        for e in tail.split(" | "):
            name = e.strip().lstrip("*").split("*(")[0]
            if name not in sp.WATCH_KEYWORDS:
                problems.append(f"Top 10 항목이 감시 단어 구절이 아니다: {name}")
                break
    # 내용 검사 (2026-11-23): 오늘 고친 오류가 다시 나오는지 모의 실행에서 잡는다.
    if "검색량 미상" in body:
        problems.append("보고서에 '검색량 미상'이 있다. 없는 숫자는 빼야 한다.")
    _bullets = 0
    _kws = []
    for b in blocks:
        if b.get("type") == "section":
            _t = b["text"]["text"]
            _bullets += _t.count("\n• ") + (1 if _t.startswith("• ") else 0)
            if "구글 트렌드 24시간" not in _t.split("\n")[0]:
                for _line in _t.split("\n")[1:]:
                    if _line.startswith("• "):
                        _m = re.search(r"\*([^*]+)\*", _line)
                        if _m:
                            _kws.append(_m.group(1))
    if "Top 10" in top:
        _counts = [int(n) for n in re.findall(r"\((\d+)\)", top.split("Top 10*:", 1)[1])]
        if _counts and (max(_counts) > 200 or max(_counts) > 2 * max(_bullets, 1)):
            problems.append(f"Top 10 가장 큰 숫자 {max(_counts)}가 항목 수 {_bullets}보다 비정상적으로 크다. 단위가 섞였다.")
    from collections import Counter as _Counter
    _dups = [k for k, c in _Counter(_kws).items() if c > 1]
    if _dups:
        problems.append(f"주제 구역에 중복 단어가 있다: {_dups[:3]}")
    _m_kr = re.search(r"🇰🇷 한국 \((\d+)건\)", body)
    if not _m_kr:
        problems.append("한국 주제가 보고서에 없다. 한국 소식 보강이 빠졌다.")
    elif int(_m_kr.group(1)) < 1:
        problems.append("한국 주제가 0건이다. 한국 소식 보강이 빠졌다.")
    # 기업 간 거래 보고서는 진짜 함수로 검사한다.
    problems.extend(check_b2b(sp))
    return problems


def check_b2b(sp):
    """기업 간 거래 보고서 본문을 진짜 함수로 돌려 오늘 고친 오류를 검사한다."""
    problems = []
    # 가져오기 함수를 가짜로 바꾼다. 네트워크 없이 진짜 판정 로직만 돌린다.
    _yields = {
        "united-states": (4.95, False),
        "china": (1.58, False),
        "south-korea": (3.82, False),
        "japan": (2.79, False),
        "malaysia": (0.0, "자료 없음"),
        "euro-area": (3.30, False),
        "switzerland": (0.53, False),
        "hong-kong": (3.91, False),
        "indonesia": (7.71, False),
        "turkey": (33.55, False),
        "israel": (0.0, "자료 없음"),
    }
    sp.get_te_yield = lambda path: _yields.get(path, (0.0, "자료 없음"))
    sp.get_frankfurter_fx = lambda: (
        {"CNY": 6.6777, "KRW": 1339.44, "JPY": 158.64, "MYR": 4.1125, "EUR": 0.9099,
         "CHF": 0.8392, "HKD": 7.8389, "IDR": 18263.0, "TRY": 50.572, "ILS": 3.3428},
        {"CNY": 6.72, "KRW": 1383.0, "JPY": 159.24, "MYR": 4.046, "EUR": 0.856,
         "CHF": 0.8027, "HKD": 7.838, "IDR": 17685.0, "TRY": 48.08, "ILS": 2.983},
    )
    sp.FX_META = {"fx_date": "2026-11-20"}
    sp.YIELD_SOURCE = {k: ("CNBC 현재값", "2026-11-23") for k in _yields}
    class _FakeChart:
        status_code = 200
        def __init__(self, url):
            self._url = url
        def json(self):
            if "^VIX" in self._url:
                return {"chart": {"result": [{"meta": {"regularMarketPrice": 35.9}}]}}
            return {"chart": {"result": [{"meta": {"regularMarketPrice": 100.0, "chartPreviousClose": 102.0}}]}}
    sp.requests.get = lambda url, headers=None, timeout=5: _FakeChart(url)
    try:
        report = sp.get_b2b_sales_report()
    except Exception as e:
        return [f"기업 간 거래 보고서 본문을 돌리다 실패했다: {e}"]
    if not report:
        return ["기업 간 거래 보고서 본문이 비어 있다."]
    if "전일 대비" not in report:
        problems.append("전광판 머리글에 '전일 대비'가 없다. 기간을 알 수 없다.")
    _us_line = ""
    for _line in report.split("\n"):
        if "미국 (나스닥/S&P500 평균)" in _line:
            _us_line = _line
            break
    # 미국 줄은 부호 있는 변동률(-4.49%)이나 자료 없음 중 하나가 있어야 한다.
    # 4.95%의 %는 금리지 변동률이 아니므로 부호 있는 %로만 본다. (2026-11-23)
    if not _us_line:
        problems.append("미국 전광판 줄이 보고서에 없다.")
    elif not re.search(r"[+-]\d+\.\d+%", _us_line) and "자료 없음" not in _us_line:
        problems.append("미국 전광판 줄에 숫자가 없다. 진입 금지만 적혀 있다.")
    if report.count("자체 규칙") != 1:
        problems.append(f"면책 문구가 {report.count('자체 규칙')}번 나온다. 머리글 1번만 있어야 한다.")
    for _line in report.split("\n"):
        if "규칙 적용 안 됨" in _line and re.search(r"\[\s*[+-]?\d+\.\d+%", _line):
            problems.append(f"규칙 적용 안 됨 줄에 합계 점수가 있다: {_line.strip()[:80]}")
            break
    for _c in ["중국", "한국", "일본", "말레이시아", "유럽", "스위스", "홍콩", "인도네시아", "터키", "이스라엘"]:
        if _c not in report:
            problems.append(f"기업 간 거래 보고서에 {_c}가 없다.")
    if report.count("판정 없음") != 2:
        problems.append(f"판정 없음이 {report.count('판정 없음')}번 나온다. 2번(말레이시아, 이스라엘)이어야 한다.")
    if "금리 자료 없음:" in report:
        problems.append("금리 자료 없음 하단 안내가 남아 있다. 환율만 보여주는 줄로 바꿔야 한다.")
    return problems


def main():
    args = [a for a in sys.argv[1:] if a != "--check-only"]
    check_only = "--check-only" in sys.argv[1:]
    path = args[0] if args else DEFAULT_PATH
    print(f"검사 대상: {path}")
    if check_only:
        print("검사만 모드: 자동 수정을 하지 않는다.")
    # 문법 검사
    try:
        import py_compile
        py_compile.compile(path, doraise=True)
        print("문법 검사 통과")
    except Exception as e:
        print(f"문법 검사 실패: {e}")
        return 1

    # 소스 정적 검사 + 자동 수정
    problems = check_source(path)
    if problems:
        print(f"소스 문제 {len(problems)}건:")
        for kind, msg in problems:
            print(f"  - [{kind}] {msg}")
        if check_only:
            return 1
        n_fixed = fix_source(path, problems)
        if n_fixed:
            print("자동 수정 뒤 다시 검사한다.")
            problems = check_source(path)
            if problems:
                print(f"자동 수정 뒤에도 남은 문제 {len(problems)}건:")
                for kind, msg in problems:
                    print(f"  - [{kind}] {msg}")
    else:
        print("소스 정적 검사 통과")

    # 모의 실행 검사
    print("모의 실행(드라이런) 검사 중...")
    try:
        dr = dry_run(path)
    except Exception as e:
        print(f"모의 실행 실패: {e}")
        return 1
    if dr:
        print(f"모의 실행 문제 {len(dr)}건:")
        for msg in dr:
            print(f"  - {msg}")
        return 1
    print("모의 실행 검사 통과")

    if problems:
        return 1
    print("전체 통과. 배포해도 된다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
