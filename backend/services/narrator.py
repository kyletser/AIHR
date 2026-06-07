"""
叙事生成器：LLM 基于已验证的分数和数据，生成文案描述、差距分析、优化建议
"""
import json
from services.llm_client import chat_json

SYSTEM_PROMPT = """你是OfferCatcher求职策略助手。你会收到已验证的简历数据、JD数据、代码计算出的分数和诊断证据。你的任务不是夸张营销，而是把“为什么匹配/不匹配、该不该投、先改哪里”说清楚。使用中文输出。

⚠️ 规则：
- detail描述要引用具体的技能名和项目名，不能模糊
- 差距分析要具体可操作
- 优化建议的original必须来自简历原文，suggested基于原文改写，不要从零编造。不能缩减原有的技术细节。
- killer_sentence选与JD最相关的技能/项目，不要选无关内容
- 不要建议伪造经历；缺技能只能建议学习/补证据，不能写成已经掌握
- strategy_insight 要直接解释“为什么推荐这个投递动作”

输出JSON：
{"dimensions":{"hard_skills":{"detail":"描述"},"projects":{"detail":"描述"},"education":{"detail":"描述"},"soft_skills":{"detail":"描述"},"industry":{"detail":"描述"},"growth":{"detail":"描述"}},"gap_analysis":[{"gap":"差距","severity":"critical/moderate/minor","suggestion":"建议","effort":"时间"}],"suggestions":[{"section":"","field":"","original":"原文","suggested":"优化版","reason":"理由","type":"rewrite/enhance/add"}],"match_verdict":"综合评语","competitive_advantage":"竞争力总结","killer_sentence":"最相关技能的一句话","strategy_insight":"投递策略解释","interview_probability":"high/medium/low"}"""


def narrate(verified: dict, scores: dict) -> dict:
    user_prompt = f"""已验证的简历数据：{json.dumps(verified['resume'], ensure_ascii=False)}
JD数据：{json.dumps(verified['jd'], ensure_ascii=False)}
各维度分数：{json.dumps(scores['dimensions'], ensure_ascii=False)}
诊断证据：{json.dumps(scores.get('diagnostics', {}), ensure_ascii=False)}
代码给出的投递策略：{json.dumps(scores.get('strategy', {}), ensure_ascii=False)}
总分：{scores['overall_score']}

请为每个维度写detail描述，生成差距分析、优化建议和一句投递策略解释。"""
    result = chat_json(SYSTEM_PROMPT, user_prompt)
    # 合并分数和文案
    for key in scores["dimensions"]:
        scores["dimensions"][key]["detail"] = result.get("dimensions", {}).get(key, {}).get("detail", "")

    scores["gap_analysis"] = result.get("gap_analysis", [])
    scores["suggestions"] = result.get("suggestions", [])
    scores["match_verdict"] = result.get("match_verdict", "")
    scores["competitive_advantage"] = result.get("competitive_advantage", "")
    scores["killer_sentence"] = result.get("killer_sentence", "")
    if scores.get("strategy"):
        scores["strategy"]["insight"] = result.get("strategy_insight", "")
    scores["interview_probability"] = result.get("interview_probability", "medium")
    return scores
