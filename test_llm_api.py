import os
from openai import OpenAI

def test():
    print("Testing NVIDIA...")
    nvidia_key = os.getenv("NVIDIA_API_KEY", "dummy")
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key, timeout=5.0, max_retries=1)
        response = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            messages=[{"role": "user", "content": "안녕"}],
            max_tokens=10
        )
        print("NVIDIA SUCCESS:", response.choices[0].message.content)
    except Exception as e:
        print("NVIDIA ERROR:", e)

    print("Testing Upstage...")
    upstage_key = os.getenv("UPSTAGE_API_KEY", "dummy")
    try:
        client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=upstage_key, timeout=5.0, max_retries=1)
        response = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[{"role": "user", "content": "안녕"}],
            max_tokens=10
        )
        print("UPSTAGE SUCCESS:", response.choices[0].message.content)
    except Exception as e:
        print("UPSTAGE ERROR:", e)

test()
