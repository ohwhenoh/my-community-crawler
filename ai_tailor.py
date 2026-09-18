import os

def generate_personalized_hook(target_name, scraped_content):
    # 1. Google Gemini API 키 확인
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash') # 가볍고 빠른 모델
            prompt = f"당신은 F5 Networks 세일즈 엔지니어입니다. 타깃 고객 '{target_name}'의 뉴스 요약({scraped_content})을 바탕으로, 이들의 비즈니스 맥락에 맞는 F5 보안 솔루션 도입 제안 멘트를 2~3문장으로 매력적으로 작성해주세요."
            response = model.generate_content(prompt)
            return f"💡 [Gemini 맞춤형 F5 제안] {response.text.strip()}"
        except Exception as e:
            return f"💡 [F5 기본 제안] {target_name} 맞춤형 솔루션을 제안합니다. (Gemini 에러: {str(e)})"
            
    # 2. OpenAI API 키 확인
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            prompt = f"당신은 F5 Networks 세일즈 엔지니어입니다. 타깃 고객 '{target_name}'의 뉴스 요약({scraped_content})을 바탕으로, 이들의 비즈니스 맥락에 맞는 F5 보안 솔루션 도입 제안 멘트를 2~3문장으로 매력적으로 작성해주세요."
            response = client.chat.completions.create(
                model="gpt-4o-mini", # 가볍고 빠른 모델
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return f"💡 [OpenAI 맞춤형 F5 제안] {response.choices[0].message.content.strip()}"
        except Exception as e:
            return f"💡 [F5 기본 제안] {target_name} 맞춤형 솔루션을 제안합니다. (OpenAI 에러: {str(e)})"

    # 키가 없을 경우 기본 멘트
    return f"💡 [F5 제안] {target_name}의 비즈니스를 F5 솔루션으로 안전하게 보호하세요. (LLM 연동 대기 중 - API 키 필요)"
