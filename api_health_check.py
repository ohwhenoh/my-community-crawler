import os
import time
from openai import OpenAI

def check_apis():
    upstage_key = os.getenv("UPSTAGE_API_KEY", "up_R94I2350T0dDYrf3w0qYFrlZxrzqC")
    nvidia_key = os.getenv("NVIDIA_API_KEY", "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")

    print("=========================================")
    print(" 🏥 AI API Health & Latency Dashboard")
    print("=========================================\n")

    # 1. NVIDIA Test
    print("[1] Testing NVIDIA NIM (Llama 3.2 11B)...")
    start_time = time.time()
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key, timeout=6.0, max_retries=0)
        res = client.chat.completions.create(
            model="meta/llama-3.2-11b-vision-instruct",
            messages=[{"role": "user", "content": "Ping"}],
            max_tokens=10
        )
        latency = time.time() - start_time
        print(f"  ✅ Status: HEALTHY | ⏱️ Latency: {latency:.2f}s | Noisy Neighbor: SAFE")
    except Exception as e:
        latency = time.time() - start_time
        print(f"  ❌ Status: UNHEALTHY | ⏱️ Latency: {latency:.2f}s | Error: {str(e)[:50]}...")

    print("\n[2] Testing Upstage (Solar Mini)...")
    start_time = time.time()
    try:
        client = OpenAI(base_url="https://api.upstage.ai/v1/solar", api_key=upstage_key, timeout=10.0, max_retries=0)
        res = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[{"role": "user", "content": "Ping"}],
            max_tokens=10
        )
        latency = time.time() - start_time
        print(f"  ✅ Status: HEALTHY | ⏱️ Latency: {latency:.2f}s")
    except Exception as e:
        latency = time.time() - start_time
        print(f"  ❌ Status: UNHEALTHY | ⏱️ Latency: {latency:.2f}s | Error: {str(e)[:50]}...")
    
    print("\n=========================================")

if __name__ == "__main__":
    check_apis()
