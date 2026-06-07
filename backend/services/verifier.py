"""
验证器：反向检查 LLM 提取的数据是否能在原文中找到依据。

这里不做评分，只留下后续评分可追溯的证据片段。这样既能降低 LLM 幻觉，
也能让匹配结果从“像一个分数”变成“有依据的诊断”。
"""
import re


SOFT_SIGNAL_PATTERNS = {
    "沟通协作": ["沟通", "协作", "团队", "跨部门", "对接", "汇报", "协调"],
    "领导力": ["负责人", "组长", "带领", "组织", "管理", "统筹", "队长"],
    "自驱力": ["自学", "独立", "主动", "从0到1", "自主", "负责"],
    "抗压能力": ["高压", "抗压", "紧急", "加班", "期限", "deadline", "多任务"],
    "学习能力": ["学习", "掌握", "快速上手", "迁移", "研究", "调研"],
    "责任心": ["负责", "维护", "上线", "交付", "保障", "排查"],
    "数据意识": ["数据", "指标", "转化率", "准确率", "qps", "延迟", "量化"],
    "服务意识": ["服务", "客户", "患者", "家长", "满意度", "投诉", "回访"],
    "合规意识": ["合规", "风控", "审查", "流程", "制度", "保密", "规范"],
    "文字表达": ["文案", "公文", "报告", "写作", "材料", "策划案", "教案"],
    "销售意识": ["销售", "谈判", "转化", "成交", "拓客", "渠道", "业绩"],
}


def _as_text(value) -> str:
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values() if v is not None)
    return str(value or "")


def _snippet(text: str, needle: str, radius: int = 90) -> str:
    if not text or not needle:
        return ""
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _find_soft_evidence(resume_text: str) -> list[dict]:
    evidence = []
    lower = resume_text.lower()
    for label, keywords in SOFT_SIGNAL_PATTERNS.items():
        hit = next((kw for kw in keywords if kw.lower() in lower), "")
        if hit:
            evidence.append({
                "skill": label,
                "keyword": hit,
                "evidence": _snippet(resume_text, hit),
            })
    return evidence


def verify_extraction(extracted: dict, resume_text: str, jd_text: str) -> dict:
    """
    对 extractor 的输出进行反向验证：
    - 每个技能必须在原文中出现（支持模糊匹配）
    - 每个项目名必须在原文中出现
    - 每个竞赛必须在原文中出现
    - 未通过验证的项直接剔除
    """
    r = extracted.get("resume", {})
    j = extracted.get("jd", {})

    # 清洗文本用于搜索
    rt_lower = resume_text.lower()
    jt_lower = jd_text.lower()

    # 技能验证：拆分复合技能（如 "Python编程" → ["Python"]），任一部分匹配即可
    verified_skills = []
    for skill in r.get("skills", []):
        skill_text = _as_text(skill)
        parts = re.split(r'[/\s,，、]+', skill_text)
        found = any(
            any(p.lower() in rt_lower for p in parts if len(p) >= 2)
            for _ in [1]  # single pass
        )
        # 更灵活：也从整体skill中去匹配
        if not found:
            # 尝试去掉常见后缀后匹配
            clean = re.sub(r'(编程|开发|语言|框架|工具|技术)$', '', skill_text).strip()
            if len(clean) >= 2 and clean.lower() in rt_lower:
                found = True
        if found:
            verified_skills.append(skill_text)

    # 项目验证
    verified_projects = []
    for proj in r.get("projects", []):
        proj_text = _as_text(proj)
        clean = re.sub(r'[（(].*?[）)]', '', proj_text).strip()  # 去括号
        if len(clean) >= 2 and clean.lower() in rt_lower:
            verified_projects.append({
                "name": proj_text,
                "evidence": _snippet(resume_text, clean),
            })

    # 竞赛验证
    verified_comps = []
    for comp in r.get("competitions", []):
        name = comp.get("name", "")
        if len(name) >= 2 and name.lower() in rt_lower:
            verified_comps.append(comp)

    # JD 技能验证
    jd_hard = []
    for skill in j.get("hard_skills", []):
        skill = _as_text(skill)
        parts = re.split(r'[/\s,，、]+', skill)
        if any(len(p) >= 2 and p.lower() in jt_lower for p in parts):
            jd_hard.append(skill)
        elif len(skill) >= 2 and skill.lower() in jt_lower:
            jd_hard.append(skill)

    jd_soft = []
    for skill in j.get("soft_skills", []):
        skill = _as_text(skill)
        if len(skill) >= 1 and skill.lower() in jt_lower:
            jd_soft.append(skill)

    soft_evidence = _find_soft_evidence(resume_text)

    return {
        "resume": {
            "skills": verified_skills,
            "projects": verified_projects,
            "competitions": verified_comps,
            "education": r.get("education", []),
            "languages": r.get("languages", []),
            "certifications": r.get("certifications", []),
            "soft_evidence": soft_evidence,
        },
        "jd": {
            "title": j.get("title", ""),
            "hard_skills": jd_hard,
            "soft_skills": jd_soft,
            "requirements": j.get("requirements", []),
            "industry": j.get("industry", ""),
            "level": j.get("level", ""),
        },
        "stats": {
            "skills_dropped": len(r.get("skills", [])) - len(verified_skills),
            "projects_dropped": len(r.get("projects", [])) - len(verified_projects),
            "comps_dropped": len(r.get("competitions", [])) - len(verified_comps),
            "jd_hard_dropped": len(j.get("hard_skills", [])) - len(jd_hard),
            "jd_soft_dropped": len(j.get("soft_skills", [])) - len(jd_soft),
        }
    }
