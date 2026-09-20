import os

def generate_personalized_hook(target_name, scraped_content):
    prompt = f"당신은 F5 Networks 최고의 B2B 보안 세일즈 엔지니어입니다. 타깃 고객 '{target_name}'의 최신 뉴스 요약({scraped_content})을 바탕으로, 이들의 비즈니스 맥락에 정확히 들어맞는 F5 보안 솔루션(Agentic AI Bot 방어, API 보안, WAF 등) 도입 제안 멘트를 2~3문장으로 아주 강력하게 작성해주세요."
    
    # 1. Upstage (Solar) API 키 확인
    upstage_key = os.getenv("UPSTAGE_API_KEY")
    if upstage_key:
        try:
            from openai import OpenAI
            client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=upstage_key)
            response = client.chat.completions.create(
                model="solar-1-mini-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return f"💡 [Upstage Solar 맞춤형 제안] {response.choices[0].message.content.strip()}"
        except Exception as e:
            pass

    # 2. NVIDIA NIM API 키 확인
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        try:
            from openai import OpenAI
            client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key)
            response = client.chat.completions.create(
                model="meta/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return f"💡 [NVIDIA Llama3 맞춤형 제안] {response.choices[0].message.content.strip()}"
        except Exception as e:
            pass

    return f"💡 [F5 기본 제안] {target_name}의 비즈니스를 F5 솔루션으로 안전하게 보호하세요. (LLM 연동 대기 중 - API 키 필요)"
