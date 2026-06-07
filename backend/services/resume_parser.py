"""
简历解析服务：将简历文本提取为结构化候选人画像
"""
from services.llm_client import chat_json

SYSTEM_PROMPT = """你是专业的简历解析器。逐段仔细阅读简历全文，不遗漏任何信息。

⚠️ 铁律：
1. 竞赛信息必提取：简历中有"蓝桥杯""ACM""竞赛""获奖""省一""铜牌""金牌""国赛"等关键词→competitions数组必须有数据。不提取竞赛信息=严重错误。
2. 软素质必须有证据：说"领导力"→必须写具体证据（如"担任社团负责人"）。证据不充分→不写该软素质，宁可少写不要编。
3. 技能全面提取：简历中出现的所有技能都要提取，不要遗漏。

输出JSON：
{
  "basic": {
    "education": [{"school":"","major":"","degree":"","graduation_year":0}],
    "graduation_year": 0,
    "target_position": "",
    "target_industry": ""
  },
  "skills": {
    "hard_skills": [{"skill":"","level":"精通/熟练/了解","source":"简历原文"}],
    "soft_skills": [{"skill":"","evidence":"具体证据（必须从简历找）"}],
    "certifications": [{"name":"","level":""}],
    "languages": [{"language":"","level":""}]
  },
  "projects": [{"name":"","role":"","duration":"","description_raw":"原文","description_star":"STAR改写","skills_demonstrated":[],"impact":""}],
  "internships": [],
  "competitions": [{"name":"","level":"国家级/省级/校级","award":"获奖等级","year":0}],
  "research": [],
  "summary": "一句话核心竞争力（60字）",
  "strengths": ["3个最大优势"]
}

缺失项填空数组[]或null，不编造。"""


def parse_resume_text(text: str) -> dict:
    user_prompt = f"请深度解析以下简历：\n\n{text}"
    return chat_json(SYSTEM_PROMPT, user_prompt)
