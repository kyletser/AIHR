"""
单次综合分析：直接将简历原文 + JD 原文发给 LLM，一次性输出匹配+优化
"""
import json
import logging
from services.llm_client import chat_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是OfferCatcher智能匹配引擎。仔细阅读下面的学生简历和JD全文，输出完整分析JSON。所有文字输出必须使用中文。

⚠️ 核心规则：
1. killer_sentence 和 competitive_advantage 必须选简历中与JD最相关的技能/项目。JD是后端开发就选RPC/IM项目，不要选课堂LSTM等不相关的项目。
2. 所有分析基于简历真实内容。killer_sentence基于真实技能。

⚠️ 优化建议铁律：
- 绝不缩减细节。原文写了"OSI七层模型、IO多路复用、MVCC、Redis缓存击穿"→建议必须保留这些具体技术术语，不能概括成"精通后端技术"
- 只增强不缩减：补充STAR量化、突出与JD匹配的关键词、优化表述顺序
- 如果原文已经很具体，不要强行优化。只改有问题的地方
- original必须是简历逐字摘录。建议版本要保持甚至增加技术细节

输出JSON：
{"dimensions":{"hard_skills":{"score":85,"detail":"具体分析，引用简历原文"},"projects":{"score":80,"detail":"列出简历中实际的项目名"},"education":{"score":90,"detail":"学历分析"},"soft_skills":{"score":70,"detail":"软素质及证据"},"industry":{"score":65,"detail":"行业匹配"},"growth":{"score":75,"detail":"竞赛获奖检查"}},"gap_analysis":[{"gap":"","severity":"critical","suggestion":"","effort":""}],"suggestions":[{"section":"","field":"","original":"从简历逐字摘录","suggested":"基于原文改写","reason":"关联JD","type":"rewrite"}],"match_verdict":"综合评语","competitive_advantage":"基于真实竞赛/项目","killer_sentence":"基于真实技能的一句话","interview_probability":"high"}

关键：score是整数0-100。有项目给分，有竞赛给分，有学历给分。所有分析内容必须能在简历原文中找到依据。"""

WEIGHTS = {"hard_skills": 35, "projects": 25, "education": 15, "soft_skills": 15, "industry": 5, "growth": 5}


def analyze_once(resume_text: str, jd_text: str) -> dict:
    user_prompt = f"=== 学生简历 ===\n{resume_text}\n\n=== 目标岗位JD ===\n{jd_text}"
    result = chat_json(SYSTEM_PROMPT, user_prompt)

    dims = result.get("dimensions", {})
    if not isinstance(dims, dict) or not dims:
        logger.error(f"DIMENSIONS MISSING! Raw result keys: {list(result.keys())}")

    total = 0
    for key, w in WEIGHTS.items():
        dim = dims.get(key, {})
        if not isinstance(dim, dict):
            dim = {}
        raw_score = dim.get("score", 0)
        # 兼容各种类型的分数：int, float, str, None
        try:
            score = int(float(str(raw_score)))
        except (ValueError, TypeError):
            score = 0
            logger.warning(f"Score parse failed: key={key}, raw={raw_score}")

        dim["score"] = score
        dim["weight"] = w
        total += score * w

    result["overall_score"] = total // 100
    result["dimensions"] = dims
    logger.info(f"Analyze done: overall={result['overall_score']}, dims={[(k,d.get('score',0)) for k,d in dims.items()]}")
    return result
