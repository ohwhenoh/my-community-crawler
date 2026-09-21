import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import yfinance as yf
import crawler_slack

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("'").strip('"')


def get_macro_email_content():
    import requests
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'})

    # 1. FX Analysis
    fx_analysis = crawler_slack.get_fx_analysis()
    
    # 2. Bond Analysis (Copied logic from generate_korean_outreach_report)
    bonds = {'미국 10년': 'IEF', '일본 10년': '2515.T', '영국 10년': 'IGLT.L', '중국 10년': 'CBON', '벨기에 10년': 'XG7S.MI', '캐나다 10년': 'XGB.TO'}
    bond_text = "📉 *[주요국 10년물 국채 가격 동향 (ETF 기반)]*\n"
    
    try:
        for country, ticker in bonds.items():
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="1y")
            if len(hist) < 5: continue
                
            curr_price = hist['Close'].iloc[-1]
            try: m1_price = hist.loc[hist.index >= (hist.index[-1] - timedelta(days=30))]['Close'].iloc[0]
            except: m1_price = curr_price
            
            if curr_price > m1_price:
                direction = "상승 📈 ➡️ [기업 대출 이자 부담 완화 🟢 / 신규 솔루션 투자 재개 기대]"
            else:
                direction = "하락 📉 ➡️ [기업 대출 이자 부담 증가 🔴 / 신규 솔루션 투자 감소 우려]"
            bond_text += f"  • {country} 국채 가격 {direction} (1개월 전: {m1_price:,.2f} ➡️ 현재: {curr_price:,.2f})\n"
    except Exception as e:
        bond_text = "  • (국채 데이터 실시간 조회 지연)\n"

    macro_text = (
        "📈 *[Global Macro & Market Signals Weekly Summary]*\n"
        "• 🟢 *Fed 금리 동향*: 동결 기조 유지 (기술주 투자 심리 안정)\n\n"
        f"{bond_text}\n"
        "• 🟡 *유로존 금리 변동*: 🇪🇺 *'독일 제조업 PMI 부진 및 유럽중앙은행(ECB) 추가 금리 인하 지연 우려'*\n\n"
        f"{fx_analysis}"
    )
    
    return macro_text

def send_email():
    load_env()
    
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    
    to_email = os.environ.get("RECIPIENT_EMAIL", "owen.choi@outlook.sg")
    
    if not smtp_user or not smtp_pass:
        print("이메일 발송 실패: .env 파일에 SMTP_USER 및 SMTP_PASS가 설정되지 않았습니다.")
        return
        
    content = get_macro_email_content()
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = f"[F5 세일즈 인텔리전스] 주간 거시경제 및 환율 리포트 ({datetime.now().strftime('%Y-%m-%d')})"
    
    body = MIMEText(content, 'plain', 'utf-8')
    msg.attach(body)
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"✅ 주간 매크로 리포트를 {to_email}로 성공적으로 전송했습니다.")
    except Exception as e:
        print(f"❌ 이메일 전송 중 에러 발생: {e}")

if __name__ == "__main__":
    send_email()
