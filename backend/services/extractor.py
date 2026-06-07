"""
结构化提取器：LLM 从简历和JD中提取结构化数据，不做分析
"""
from services.llm_client import chat_json

SYSTEM_PROMPT = """你是精准的数据提取器。从简历和JD中提取结构化信息，不做任何分析、评分或建议。只输出JSON。

⚠️ 提取规则：
- 技能：从简历中列出所有可用于求职匹配的能力/工具/方法/证书关键词。技术、财务、教学、医疗、法律、销售、运营、设计、制造、公务员等行业都要覆盖。
- 项目：这里的 projects 不是只指技术项目，也包括实习经历、校园实践、课题研究、作品集、销售/运营案例、教学实践、临床/护理实践、行政/社团工作等能证明能力的经历名称。
- 竞赛/荣誉：如果简历提到"竞赛""获奖""优秀学生""奖学金""蓝桥杯""ACM""国奖""省一"等关键词，必须提取。
- 学历：提取学校名、专业、学位、毕业年份。
- JD技能：JD中 hard_skills 表示岗位关键能力，包含专业技能、工具、证书、业务知识、方法论、语言要求、合规要求等，不限于互联网技术。
- soft_skills 是软素质要求，硬门槛是学历/证书/年限/资格证/政治面貌等要求。
- 所有字段都可以为null或空数组，不要编造。

输出JSON：
{
  "resume": {
    "skills": ["技能1","技能2"],
    "projects": ["项目1","项目2"],
    "competitions": [{"name":"竞赛名","award":"获奖","year":2024}],
    "education": [{"school":"学校","major":"专业","degree":"学历","year":2025}],
    "languages": ["英语六级","普通话"],
    "certifications": ["证书名"]
  },
  "jd": {
    "title": "岗位名",
    "hard_skills": ["必须技能","加分技能"],
    "soft_skills": ["沟通","协作"],
    "requirements": [{"requirement":"学历本科","type":"hard"},{"requirement":"3年经验","type":"hard"}],
    "industry": "行业",
    "level": "初级/中级/高级"
  }
}"""


def extract(resume_text: str, jd_text: str) -> dict:
    user_prompt = f"简历：\n{resume_text}\n\nJD：\n{jd_text}"
    return chat_json(SYSTEM_PROMPT, user_prompt)
