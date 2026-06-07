"""
评分引擎：证据驱动的 6 维匹配评分。

设计目标：
- LLM 负责抽取，代码负责稳定评分。
- 不只给总分，还输出匹配证据、风险雷达和下一步投递策略。
"""
import json
import re


WEIGHTS = {
    "hard_skills": 35,
    "projects": 25,
    "education": 15,
    "soft_skills": 15,
    "industry": 5,
    "growth": 5,
}

SYNONYMS = {
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "golang": "go",
    "go语言": "go",
    "js": "javascript",
    "ts": "typescript",
    "es6": "javascript",
    "es6+": "javascript",
    "cpp": "c++",
    "cplus": "c++",
    "c++": "c++",
    "py": "python",
    "db": "数据库",
    "dbms": "数据库",
    "nosql": "redis",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "vuejs": "vue",
    "reactjs": "react",
    "ppt": "powerpoint",
    "powerpoint": "powerpoint",
    "word文档": "word",
    "msword": "word",
    "wps": "office",
    "excel表": "excel",
    "ps": "photoshop",
    "ai": "illustrator",
    "cad": "autocad",
    "普通话证": "普通话",
    "教师资格": "教师资格证",
    "教资": "教师资格证",
    "执业医师": "医师资格证",
    "护资": "护士资格证",
    "法考": "法律职业资格",
}

OCCUPATION_DOMAINS = {
    "software": ["python", "java", "go", "c++", "mysql", "redis", "linux", "docker", "kubernetes", "rpc", "spring", "vue", "react", "前端", "后端", "算法", "数据结构"],
    "data_ai": ["python", "sql", "excel", "tableau", "powerbi", "机器学习", "深度学习", "数据分析", "统计", "建模", "报表", "指标"],
    "product_ops": ["产品", "需求", "原型", "用户", "竞品", "运营", "增长", "活动", "转化率", "sop", "流程优化"],
    "sales_marketing": ["销售", "市场", "营销", "客户", "渠道", "商务", "谈判", "成交", "投放", "品牌", "新媒体", "文案"],
    "finance_accounting": ["金融", "银行", "证券", "风控", "合规", "财务", "财会", "会计", "会计准则", "初级会计证", "凭证", "费用审核", "审计", "税务", "预算", "报表"],
    "education_training": ["教学", "课程", "教师", "教研", "培训", "教案", "班主任", "家校沟通", "教师资格证"],
    "healthcare": ["医疗", "临床", "护理", "患者", "病历", "诊疗", "药学", "检验", "医师资格证", "护士资格证"],
    "legal_public": ["法律", "法务", "合同", "诉讼", "合规", "公文", "党建", "政策", "公务员", "选调", "行政", "法律职业资格"],
    "hr_admin": ["人力", "招聘", "培训", "绩效", "薪酬", "员工关系", "行政", "档案", "会议", "office"],
    "manufacturing_supply": ["机械", "制造", "工艺", "质量", "供应链", "采购", "物流", "仓储", "autocad", "solidworks", "生产"],
    "design_media": ["设计", "视觉", "交互", "figma", "photoshop", "illustrator", "剪辑", "视频", "内容", "作品集"],
    "research_consulting": ["研究", "课题", "论文", "调研", "访谈", "咨询", "报告", "竞品", "行业分析", "实验"],
    "customer_service": ["客服", "客户成功", "服务", "投诉", "回访", "满意度", "续费", "客诉", "患者", "家长"],
}

TRANSFERABLE_BY_DOMAIN = {
    "software": ["系统", "逻辑", "问题排查", "数据", "自动化", "工程化"],
    "data_ai": ["数据", "统计", "excel", "分析", "报告", "量化"],
    "product_ops": ["调研", "沟通", "项目管理", "数据", "流程", "用户"],
    "sales_marketing": ["沟通", "客户", "文案", "活动", "数据", "谈判"],
    "finance_accounting": ["数据", "合规", "风险", "严谨", "excel", "报表"],
    "education_training": ["表达", "课程", "沟通", "耐心", "组织", "教案"],
    "healthcare": ["严谨", "患者", "记录", "规范", "沟通", "责任心"],
    "legal_public": ["文字", "合规", "政策", "材料", "逻辑", "流程"],
    "hr_admin": ["沟通", "组织", "流程", "文档", "协调", "服务"],
    "manufacturing_supply": ["流程", "质量", "数据", "现场", "协调", "成本"],
    "design_media": ["审美", "用户", "表达", "作品", "内容", "沟通"],
    "research_consulting": ["调研", "报告", "数据", "分析", "访谈", "逻辑"],
    "customer_service": ["服务", "沟通", "客户", "耐心", "问题解决", "记录"],
}

PROGRAMMING_LANGUAGES = {"python", "java", "go", "c++", "javascript", "typescript"}

INDUSTRY_HINTS = {
    "finance_accounting": ["金融", "财会", "会计", "审计", "税务", "银行", "证券"],
    "education_training": ["教育", "教师", "教学", "培训", "学校"],
    "healthcare": ["医疗", "临床", "护理", "医生", "医院", "药学"],
    "legal_public": ["公务员", "公共", "政府", "法务", "法律", "选调", "行政"],
    "manufacturing_supply": ["制造", "机械", "供应链", "采购", "物流", "生产"],
    "sales_marketing": ["销售", "市场", "营销", "商务", "品牌"],
    "design_media": ["设计", "传媒", "视觉", "内容", "视频"],
    "hr_admin": ["人力", "招聘", "行政", "人事"],
    "software": ["互联网", "软件", "开发", "工程师"],
}

COMPETITION_BONUS = {
    "国际": 45,
    "国家级": 38,
    "全国": 38,
    "省级": 25,
    "校级": 10,
    "一等奖": 30,
    "二等奖": 22,
    "三等奖": 15,
    "金牌": 38,
    "银牌": 30,
    "铜牌": 22,
    "acm": 35,
    "蓝桥杯": 28,
}

DEGREE_LEVEL = {"博士": 4, "硕士": 3, "研究生": 3, "本科": 2, "大专": 1}
DEGREE_SCORE = {4: 95, 3: 86, 2: 74, 1: 48, 0: 58}


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def _to_text(value) -> str:
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values() if v is not None)
    return str(value or "")


def _project_name(project) -> str:
    if isinstance(project, dict):
        return str(project.get("name") or "")
    return str(project or "")


def _project_evidence(project) -> str:
    if isinstance(project, dict):
        return str(project.get("evidence") or project.get("name") or "")
    return str(project or "")


def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("c plus plus", "c++")
    text = re.sub(r"[^\w\+\u4e00-\u9fff]", "", text)
    return SYNONYMS.get(text, text)


def _contains_skill(haystack: str, skill: str) -> bool:
    h = _normalize(haystack)
    s = _normalize(skill)
    if not s:
        return False
    return s in h or h in s


def _skill_match_info(resume_skills: list[str], jd_skills: list[str]) -> dict:
    resume_norm = [_normalize(s) for s in resume_skills]
    matched = []
    missing = []
    alternatives = []
    for skill in jd_skills:
        canonical = _normalize(skill)
        if any(canonical == r or canonical in r or r in canonical for r in resume_norm):
            matched.append(skill)
        else:
            missing.append(skill)

    matched_langs = {_normalize(s) for s in matched if _normalize(s) in PROGRAMMING_LANGUAGES}
    jd_langs = {_normalize(s) for s in jd_skills if _normalize(s) in PROGRAMMING_LANGUAGES}
    if matched_langs and len(jd_langs) >= 2:
        strict_missing = []
        for skill in missing:
            if _normalize(skill) in PROGRAMMING_LANGUAGES:
                alternatives.append(skill)
            else:
                strict_missing.append(skill)
        missing = strict_missing

    return {"matched": matched, "missing": missing, "alternatives": alternatives}


def _domain_scores(text: str) -> dict:
    norm = _normalize(text)
    scores = {}
    for domain, keywords in OCCUPATION_DOMAINS.items():
        scores[domain] = sum(1 for kw in keywords if _normalize(kw) in norm)
    return scores


def _top_domains(text: str, limit: int = 2) -> list[str]:
    scores = _domain_scores(text)
    return [name for name, count in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit] if count > 0]


def _hint_domains(text: str) -> list[str]:
    hits = []
    for domain, keywords in INDUSTRY_HINTS.items():
        if any(kw.lower() in text.lower() for kw in keywords):
            hits.append(domain)
    return hits


def _merge_domains(*groups: list[str], limit: int = 4) -> list[str]:
    merged = []
    for group in groups:
        for item in group:
            if item and item not in merged:
                merged.append(item)
    return merged[:limit]


def _transferable_hits(resume_text: str, jd_domains: list[str], direct_matched: list[str]) -> list[str]:
    direct_text = " ".join(direct_matched).lower()
    hits = []
    for domain in jd_domains:
        for signal in TRANSFERABLE_BY_DOMAIN.get(domain, []):
            signal_lower = signal.lower()
            if signal_lower in resume_text and signal_lower not in direct_text and signal not in hits:
                hits.append(signal)
    return hits[:5]


def _hard_skill_score(resume_skills: list[str], jd_skills: list[str], jd_domains: list[str]) -> tuple[int, dict]:
    if not jd_skills:
        return 62, {"matched": [], "missing": [], "transferable": [], "coverage": 1.0}

    info = _skill_match_info(resume_skills, jd_skills)
    effective_required = len(info["matched"]) + len(info["missing"])
    coverage = len(info["matched"]) / max(1, effective_required)
    resume_text = " ".join(resume_skills).lower()
    transferable = _transferable_hits(resume_text, jd_domains, info["matched"])
    alternative_credit = min(10, len(info.get("alternatives", [])) * 3)
    score = 18 + coverage * 72 + min(10, len(transferable) * 3) + alternative_credit

    if not info["matched"] and transferable:
        score = max(score, 42)
    if len(info["missing"]) >= max(2, len(jd_skills) // 2 + 1):
        score -= 8

    return _clamp(score, 12, 100), {
        **info,
        "transferable": transferable,
        "coverage": round(coverage, 2),
    }


def _project_score(projects: list, resume_skills: list[str], jd_skills: list[str], jd_text: str, jd_domains: list[str]) -> tuple[int, dict]:
    if not projects:
        return 18, {"relevant_projects": [], "coverage": 0}

    relevant = []
    jd_terms = " ".join(jd_skills + jd_domains + [jd_text]).lower()
    for project in projects:
        name = _project_name(project)
        evidence = _project_evidence(project)
        evidence_norm = _normalize(name + " " + evidence)
        skill_hits = [skill for skill in jd_skills if _normalize(skill) and _normalize(skill) in evidence_norm]
        domain_hits = _top_domains(evidence, 3)
        domain_overlap = [d for d in domain_hits if d in jd_domains]
        text_overlap = any(token in evidence.lower() for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", jd_terms)[:40])
        if skill_hits or domain_overlap or text_overlap:
            relevant.append({
                "name": name,
                "skill_hits": skill_hits[:4],
                "domain_hits": domain_overlap[:3],
                "evidence": evidence,
            })

    coverage = len(relevant) / max(1, len(projects))
    evidence_density = min(1.0, len(set(resume_skills)) / 12)
    score = 28 + coverage * 52 + evidence_density * 15 + min(5, len(projects) * 2)
    if not relevant and projects:
        score = 34 + min(16, len(projects) * 4)

    return _clamp(score, 15, 100), {
        "relevant_projects": relevant[:4],
        "coverage": round(coverage, 2),
    }


def _degree_level(education: list) -> int:
    best = 0
    for edu in education:
        text = _to_text(edu).lower()
        for degree, level in DEGREE_LEVEL.items():
            if degree in text:
                best = max(best, level)
    return best or (2 if education else 0)


def _required_degree(requirements: list) -> int:
    required = 0
    for req in requirements:
        text = _to_text(req).lower()
        for degree, level in DEGREE_LEVEL.items():
            if degree in text:
                required = max(required, level)
    return required


def _education_score(education: list, requirements: list) -> tuple[int, dict]:
    candidate = _degree_level(education)
    required = _required_degree(requirements)
    if not education:
        return 18, {"candidate_level": 0, "required_level": required, "status": "missing"}
    if not required:
        return DEGREE_SCORE.get(candidate, 58), {"candidate_level": candidate, "required_level": 0, "status": "no_strict_requirement"}
    if candidate >= required:
        return _clamp(DEGREE_SCORE.get(candidate, 58) + 10), {"candidate_level": candidate, "required_level": required, "status": "met"}
    gap = required - candidate
    return _clamp(58 - gap * 18, 20, 72), {"candidate_level": candidate, "required_level": required, "status": "below_requirement"}


def _soft_score(resume_soft: list[dict], jd_soft: list[str]) -> tuple[int, dict]:
    if not jd_soft:
        score = 48 + min(32, len(resume_soft) * 8)
        return _clamp(score, 35, 88), {"matched": [], "evidence": resume_soft[:5], "coverage": 1.0}

    matched = []
    soft_text = " ".join(_to_text(item) for item in resume_soft)
    for skill in jd_soft:
        if any(part in soft_text for part in re.split(r"[/、，,\s]+", skill) if part):
            matched.append(skill)
    coverage = len(matched) / max(1, len(jd_soft))
    score = 30 + coverage * 52 + min(18, len(resume_soft) * 4)
    return _clamp(score, 18, 100), {"matched": matched, "evidence": resume_soft[:5], "coverage": round(coverage, 2)}


def _industry_score(resume_skills: list[str], projects: list, jd: dict) -> tuple[int, dict]:
    resume_text = " ".join(resume_skills + [_project_evidence(p) for p in projects]).lower()
    jd_text = " ".join([jd.get("industry") or "", jd.get("title") or ""] + jd.get("hard_skills", [])).lower()
    resume_domains = _merge_domains(_hint_domains(resume_text), _top_domains(resume_text, 4), limit=4)
    jd_domains = _merge_domains(_hint_domains(jd_text), _top_domains(jd_text, 3), limit=3)
    overlap = [d for d in resume_domains if d in jd_domains]
    if not jd_domains:
        return 58, {"resume_domains": resume_domains, "jd_domains": [], "overlap": []}
    score = 36 + (len(overlap) / max(1, len(jd_domains))) * 54 + min(10, len(resume_domains) * 2)
    return _clamp(score, 25, 100), {"resume_domains": resume_domains, "jd_domains": jd_domains, "overlap": overlap}


def _competitive_score(competitions: list, skills: list[str], projects: list, languages: list, certs: list) -> tuple[int, dict]:
    score = 28
    comp_signals = []
    for comp in competitions:
        text = json.dumps(comp, ensure_ascii=False).lower() if isinstance(comp, dict) else str(comp).lower()
        for keyword, bonus in COMPETITION_BONUS.items():
            if keyword.lower() in text:
                score += bonus
                comp_signals.append(keyword)
                break

    score += min(18, len(set(_normalize(s) for s in skills)) * 2)
    score += min(14, len(projects) * 5)
    score += min(8, len(languages) * 4)
    score += min(8, len(certs) * 4)
    return _clamp(score, 18, 100), {
        "competition_signals": comp_signals,
        "skill_breadth": len(set(_normalize(s) for s in skills)),
        "project_count": len(projects),
    }


def _dimension(score_value: int, weight: int, reason: str, diagnostics: dict) -> dict:
    return {"score": score_value, "weight": weight, "reason": reason, "diagnostics": diagnostics}


def _strategy(overall: int, dimensions: dict, diagnostics: dict) -> dict:
    missing = diagnostics.get("skills", {}).get("missing", [])
    risks = []
    for key, label in [
        ("hard_skills", "关键能力覆盖"),
        ("projects", "经历证据"),
        ("soft_skills", "通用素质证据"),
        ("education", "门槛资质"),
    ]:
        score_value = dimensions[key]["score"]
        if score_value < 55:
            risks.append({"label": label, "level": "high", "reason": dimensions[key]["reason"]})
        elif score_value < 72:
            risks.append({"label": label, "level": "medium", "reason": dimensions[key]["reason"]})

    if overall >= 82 and not any(r["level"] == "high" for r in risks):
        action = "优先投递"
        tone = "匹配度较强，可以把主要精力放在简历关键词和项目亮点排序上。"
    elif overall >= 68:
        action = "优化后投递"
        tone = "有可投价值，但建议先补强最影响初筛的1-2个证据点。"
    elif overall >= 55:
        action = "谨慎投递"
        tone = "更适合作为冲刺岗位，先用短周期补短板或调整目标岗位。"
    else:
        action = "暂缓投递"
        tone = "当前差距会明显影响初筛，建议先换更贴近的岗位或做能力补齐。"

    learning_sprints = []
    for skill in missing[:3]:
        learning_sprints.append({
            "target": skill,
            "plan": f"围绕 {skill} 补一条可验证证据：作品/案例/证书/实践记录任选其一",
            "effort": "3-7天" if len(skill) <= 10 else "1-2周",
        })

    resume_focus = []
    if dimensions["projects"]["score"] < 75:
        resume_focus.append("把最贴近JD的经历提前，并写清场景、职责、动作、结果和可量化产出")
    if missing:
        resume_focus.append("能力/证书栏区分“已掌握/学习中/可迁移”，不要把未具备项写成已具备")
    if dimensions["soft_skills"]["score"] < 72:
        resume_focus.append("用协作对象、服务对象、交付结果或问题处理案例补足软素质证据")

    return {
        "recommended_action": action,
        "positioning": tone,
        "risk_radar": risks[:4],
        "learning_sprints": learning_sprints,
        "resume_focus": resume_focus[:3],
    }


def score(verified: dict) -> dict:
    """
    输入：verifier 验证后的数据
    输出：6 维分数、诊断证据、投递策略
    """
    r = verified["resume"]
    j = verified["jd"]

    skills = r.get("skills", [])
    projects = r.get("projects", [])
    jd_skills = j.get("hard_skills", [])
    jd_text = " ".join([j.get("title") or "", j.get("industry") or ""] + jd_skills)
    jd_domains = _merge_domains(_hint_domains(jd_text), _top_domains(jd_text, 3), limit=3)

    hard_score, hard_diag = _hard_skill_score(skills, jd_skills, jd_domains)
    project_score, project_diag = _project_score(projects, skills, jd_skills, jd_text, jd_domains)
    education_score, education_diag = _education_score(r.get("education", []), j.get("requirements", []))
    soft_score, soft_diag = _soft_score(r.get("soft_evidence", []), j.get("soft_skills", []))
    industry_score, industry_diag = _industry_score(skills, projects, j)
    growth_score, growth_diag = _competitive_score(
        r.get("competitions", []),
        skills,
        projects,
        r.get("languages", []),
        r.get("certifications", []),
    )

    dimensions = {
        "hard_skills": _dimension(
            hard_score,
            WEIGHTS["hard_skills"],
            f"JD技能命中 {len(hard_diag['matched'])}/{max(1, len(hard_diag['matched']) + len(hard_diag['missing']))}",
            hard_diag,
        ),
        "projects": _dimension(
            project_score,
            WEIGHTS["projects"],
            f"相关项目 {len(project_diag['relevant_projects'])}/{max(1, len(projects))}",
            project_diag,
        ),
        "education": _dimension(
            education_score,
            WEIGHTS["education"],
            f"学历状态：{education_diag['status']}",
            education_diag,
        ),
        "soft_skills": _dimension(
            soft_score,
            WEIGHTS["soft_skills"],
            f"软素质证据 {len(soft_diag['evidence'])} 条",
            soft_diag,
        ),
        "industry": _dimension(
            industry_score,
            WEIGHTS["industry"],
            f"方向重合：{len(industry_diag['overlap'])} 个",
            industry_diag,
        ),
        "growth": _dimension(
            growth_score,
            WEIGHTS["growth"],
            f"技能广度 {growth_diag['skill_breadth']}，项目 {growth_diag['project_count']} 个",
            growth_diag,
        ),
    }

    overall = sum(dimensions[key]["score"] * weight for key, weight in WEIGHTS.items()) // 100
    diagnostics = {
        "skills": hard_diag,
        "projects": project_diag,
        "soft": soft_diag,
        "industry": industry_diag,
        "growth": growth_diag,
    }

    return {
        "overall_score": overall,
        "dimensions": dimensions,
        "diagnostics": diagnostics,
        "strategy": _strategy(overall, dimensions, diagnostics),
    }
