import json
import logging
import time
import httpx
from config import get_provider_config

logger = logging.getLogger(__name__)
TIMEOUT = 180  # 保证长文本有足够处理时间


def chat_json(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict:
    """
    通过 httpx 直接调用智谱/DeepSeek/硅基流动 API，输出 JSON。
    绕过 OpenAI SDK 的连接池和代理问题。
    """
    cfg = get_provider_config()
    base_url = cfg["base_url"].rstrip("/")
    model = cfg["model"]
    api_key = cfg["api_key"]

    # API URL（三家都是 OpenAI 兼容的 /chat/completions）
    url = f"{base_url}/chat/completions"

    # Prompt 中追加 JSON 约束
    full_system = system_prompt + "\n\n你必须只输出合法的 JSON 对象，不要包含 Markdown 代码块标记，不要有任何解释文字。"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 8192,
    }

    logger.info(f"LLM direct call: model={model}, url={url}, input_len={len(user_prompt)} chars")

    for attempt in range(2):
        try:
            with httpx.Client(timeout=TIMEOUT, proxy=None, follow_redirects=True) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            raw = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            logger.info(f"LLM response: {len(raw)} chars, tokens={usage}")

            # 自清理 Markdown 包裹
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            raw = raw.strip()

            return json.loads(raw)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed (attempt {attempt+1}): {e}")
            if attempt == 0:
                payload["messages"].append({
                    "role": "user",
                    "content": "上次输出 JSON 解析失败。请只输出纯 JSON，去掉 ``` 标记。"
                })
            else:
                raise RuntimeError(f"JSON 解析失败: {e}\n原始输出前200字: {raw[:200]}")

        except httpx.HTTPStatusError as e:
            detail = e.response.text[:500] if e.response else str(e)
            status = e.response.status_code
            logger.error(f"API HTTP error (attempt {attempt+1}): {status} - {detail}")

            # 速率限制 (429)：等待后重试，最多 3 次
            if status == 429:
                wait = (attempt + 1) * 5  # 5s, 10s, 15s...
                logger.info(f"Rate limited, waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            if attempt == 0:
                continue
            raise RuntimeError(f"API 返回 {status}: {detail}")

        except httpx.TimeoutException:
            logger.error(f"API timeout (attempt {attempt+1})")
            if attempt == 0:
                continue
            raise RuntimeError(f"API 超时（{TIMEOUT}秒），请检查网络或换用更快的模型")

        except Exception as e:
            logger.error(f"API error (attempt {attempt+1}): {type(e).__name__}: {e}")
            if attempt == 0:
                continue
            raise

    return {}
