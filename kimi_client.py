import time
import random
import requests

class KimiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.moonshot.cn/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

        self.session = requests.Session()
        self.session.trust_env = False  # 继续保持：不吃系统代理

    def chat(self, messages, temperature=0.2, max_tokens=2000, model=None):
        if model is None:
            import os
            model = os.getenv("KIMI_TEXT_MODEL", "moonshot-v1-8k")
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # ✅ 429 自动退避重试：最多重试 6 次（约 1~30s）
        for attempt in range(6):
            resp = self.session.post(url, headers=headers, json=payload, timeout=120)

            if resp.status_code == 429:
                # 优先尊重服务端的 Retry-After
                ra = resp.headers.get("Retry-After")
                if ra:
                    sleep_s = float(ra)
                else:
                    # 指数退避 + 抖动
                    sleep_s = min(30.0, (2 ** attempt)) + random.uniform(0, 0.5)

                time.sleep(sleep_s)
                continue

            resp.raise_for_status()
            data = resp.json()

            # 兼容不同返回结构
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            return data

        raise RuntimeError("触发限流(429)且多次重试仍失败：请稍后再试或降低请求频率。")
