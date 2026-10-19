import os
import logging
from openai import OpenAI

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_TAILOR")

def validate_quality(text):
    """가드레일(Guardrail): AI가 생성한 텍스트의 품질을 엄격히 검증합니다."""
    if not text or len(text) < 15:
        return False
    # AI가 헛소리를 하거나 다른 솔루션을 팔지 않도록 검증
    if "f5" not in text.lower() and "보안" not in text.lower():
        return False
    return True

def generate_personalized_hook(target_name, scraped_content):
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    upstage_key = os.getenv("UPSTAGE_API_KEY")
    
    # 촘촘한 가드레일이 적용된 강력한 프롬프트 (Prompt Engineering 최적화)
    prompt = f"""
당신은 F5 Networks의 최고 B2B 보안 세일즈 엔지니어입니다.
고객사 '{target_name}'의 최근 동향({scraped_content[:500]})을 분석하여 세일즈 제안 멘트를 작성하세요.

[가드레일 제약사항 - 반드시 지킬 것]
1. 반드시 2~3문장 이내로 짧고 강렬하게 작성할 것.
2. 'F5'라는 단어와 'Agentic AI', 'WAF', 'API 보안' 중 하나를 반드시 포함할 것.
3. 환각(거짓 정보)을 만들지 말고 제공된 맥락에만 기반할 것.
4. "~하시길 바랍니다", "~을 제안합니다" 등의 정중하고 신뢰감 있는 비즈니스 톤을 유지할 것.
"""

    # 1. 퀄리티가 좋은 NVIDIA NIM(Llama 3.2) 최우선 시도
    # Noisy Neighbor 해결책: 타임아웃을 6초로 짧게 주고, 실패 시 즉시 다음으로 넘어가도록 설정
    if nvidia_key:
        logger.info("[Health Check] NVIDIA NIM API 상태 체크 및 생성 시도...")
        try:
            client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key, timeout=6.0, max_retries=1)
            response = client.chat.completions.create(
                model="meta/llama-3.2-11b-vision-instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            result = response.choices[0].message.content.strip()
            if validate_quality(result):
                return f"💡 [NVIDIA Llama3.2 맞춤형 제안] {result}"
            else:
                logger.warning("NVIDIA 결과물이 품질 가드레일을 통과하지 못했습니다.")
        except Exception as e:
            logger.warning(f"⚠️ NVIDIA API 지연/실패 (Noisy Neighbor 감지, 우회 중): {e}")

    # 2. NVIDIA 실패 시 Upstage (Solar)로 스마트 폴백(Smart Fallback)
    if upstage_key:
        logger.info("[Health Check] Upstage Solar API 폴백 구동 중...")
        try:
            client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=upstage_key, timeout=10.0, max_retries=2)
            response = client.chat.completions.create(
                model="solar-1-mini-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            result = response.choices[0].message.content.strip()
            if validate_quality(result):
                return f"💡 [Upstage Solar 맞춤형 제안] {result}"
            else:
                logger.warning("Upstage 결과물이 품질 가드레일을 통과하지 못했습니다.")
        except Exception as e:
            logger.warning(f"⚠️ Upstage API 실패: {e}")

    # 3. 두 API 모두 장애 발생 시 최후의 보루 (시스템 중단 방지)
    return f"💡 [F5 제안] {target_name}의 트래픽과 데이터를 F5 Distributed Cloud로 안전하게 보호하십시오. (AI망 일시적 혼잡)"

