import os
from dotenv import load_dotenv

load_dotenv()

# === LLM Provider & Model ===

# 可选: deepseek / siliconflow / zhipu
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")

PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "json_support": True,  # 原生支持 response_format json_object
    },
    "siliconflow": {
        "name": "硅基流动 (SiliconFlow)",
        "api_key": os.getenv("SILICONFLOW_API_KEY", ""),
        "base_url": os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        "model": os.getenv("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3"),
        "json_support": True,
    },
    "zhipu": {
        "name": "智谱 (ZhipuAI)",
        "api_key": os.getenv("ZHIPU_API_KEY", ""),
        "base_url": os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        "model": os.getenv("ZHIPU_MODEL", "glm-4-flash"),
        "json_support": False,  # 智谱 GLM 系列对 json_object 支持不稳定，用 prompt 约束替代
        "need_sse_fix": False,
    },
}


def get_provider_config():
    """获取当前激活的 LLM Provider 配置"""
    if LLM_PROVIDER not in PROVIDERS:
        raise ValueError(f"不支持的 LLM Provider: {LLM_PROVIDER}，可选: {list(PROVIDERS.keys())}")
    return PROVIDERS[LLM_PROVIDER]


# === Database ===

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./offer_catcher.db")
