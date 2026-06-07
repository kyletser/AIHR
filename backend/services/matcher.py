"""
能力匹配引擎：智能对比候选人画像与JD基因（全行业通用）
"""
import json
from services.llm_client import chat_json

SYSTEM_PROMPT = """你是OfferCatcher首席匹配分析师。先仔细阅读候选人画像中的所有信息，再逐项评分。0分只能用于候选人完全没有任何相关数据的情况，有数据就必须给合理分。

给每个维度独立打分（0-100），不需要计算总分，代码会自动算。

输出JSON（key名必须完全一致）：
{
  "dimensions": {
    "hard_skills": {"score": 0, "comment": "具体分析：候选人有哪些硬技能，JD要求哪些，匹配/缺失了什么"},
    "projects": {"score": 0, "comment": "具体分析：候选人的项目(列出项目名)与岗位JD的实质相关度"},
    "education": {"score": 0, "comment": "具体分析：学历学校专业是否满足JD要求"},
    "soft_skills": {"score": 0, "comment": "具体分析：候选人软素质体现及证据"},
    "industry": {"score": 0, "comment": "具体分析：行业匹配度"},
    "growth": {"score": 0, "comment": "具体分析：竞赛获奖（必须检查画像中的competitions字段！）、技能演进、学习轨迹"}
  },
  "gap_analysis": [{"gap":"","severity":"critical/moderate/minor","suggestion":"","effort":"估计时间"}],
  "competitive_advantage": "",
  "match_verdict": "",
  "interview_probability": "high/medium/low"
}

评分铁律：
- projects: 候选人画像里有projects数组，有项目就给分！有3个复杂项目不给0分
- education: 候选人画像里有education字段，有学历信息就给分！
- growth: 检查画像中的competitions数组！有蓝桥杯/ACM/竞赛获奖→必须给分！说"没有竞赛记录"但competitions数组有数据=严重错误
- soft_skills: 只从画像中的soft_skills数组提取，每条必须带evidence，没有证据的不写
- 0分=候选人画像中该字段完全为空或null。有数据必须给分"""


def match_candidate(resume_profile: dict, jd_dna: dict) -> dict:
    user_prompt = f"候选人画像：{json.dumps(resume_profile, ensure_ascii=False)}\n\nJD基因：{json.dumps(jd_dna, ensure_ascii=False)}\n\n请进行深度匹配分析。"
    result = chat_json(SYSTEM_PROMPT, user_prompt)

    # 代码计算加权总分（不靠 LLM 算数）
    WEIGHTS = {
        "hard_skills": 35, "projects": 25, "education": 15,
        "soft_skills": 15, "industry": 5, "growth": 5,
    }
    dims = result.get("dimensions", {})
    total = 0
    for key, w in WEIGHTS.items():
        score = int(dims.get(key, {}).get("score", 0))
        total += score * w
        # LLM 输出 comment → 映射为前端用的 detail
        dims[key]["detail"] = dims[key].pop("comment", "")
        dims[key]["weight"] = w

    result["overall_score"] = total // 100  # 加权总分
    result["dimensions"] = dims
    return result
