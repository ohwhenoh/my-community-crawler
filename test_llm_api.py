import os
from openai import OpenAI

with open(".env", "r") as f:
    for line in f:
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ[k] = v.strip('"\'')

def test():
    print("Testing NVIDIA...")
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "dummy")
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key, timeout=30.0, max_retries=1)
        response = client.chat.completions.create(
            model="meta/llama-3.2-11b-vision-instruct",
            messages=[{"role": "user", "content": "안녕"}],
            max_tokens=10
        )
        print("NVIDIA SUCCESS:", response.choices[0].message.content)
    except Exception as e:
        print("NVIDIA ERROR:", e)

test()
