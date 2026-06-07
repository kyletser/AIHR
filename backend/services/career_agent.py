"""
求职智能体策略层。

这些能力不依赖额外 LLM 调用，基于已验证画像、JD、评分和投递历史生成：
- 目标岗位规划
- 多轮追问信息缺口
- 简历版本草稿
- 投递反馈洞察
"""
from __future__ import annotations

import re
from statistics import mean

from models.db_models import Application, MatchRecord, Resume
from services.llm_client import chat_json


ROLE_PROFILES = [
    {
        "role": "财务/审计/银行业务",
        "keywords": ["财务", "会计", "审计", "税务", "银行", "金融", "风控", "预算", "报表", "excel"],
        "evidence": ["初级会计证", "财务实习", "费用审核", "凭证", "银行", "金融"],
        "starter_jd_keywords": ["Excel", "报表", "合规", "客户服务", "审计资料"],
    },
    {
        "role": "教育培训/教研教师",
        "keywords": ["教学", "教师", "课程", "教研", "培训", "教案", "家校", "表达"],
        "evidence": ["教师资格证", "家教", "助教", "授课", "班主任", "课程设计"],
        "starter_jd_keywords": ["教师资格证", "学科基础", "课堂管理", "家校沟通", "教研"],
    },
    {
        "role": "医疗健康/临床护理",
        "keywords": ["医疗", "临床", "护理", "患者", "病历", "诊疗", "药学", "检验"],
        "evidence": ["医师资格证", "护士资格证", "医院", "病历", "实习", "患者沟通"],
        "starter_jd_keywords": ["病历书写", "患者沟通", "临床规范", "资格证", "责任心"],
    },
    {
        "role": "公共事务/行政综合",
        "keywords": ["公文", "行政", "政策", "党建", "会议", "材料", "档案", "协调", "公务员"],
        "evidence": ["学生干部", "党员", "材料写作", "会议组织", "社团负责人"],
        "starter_jd_keywords": ["公文写作", "组织协调", "Office", "服务意识", "流程执行"],
    },
    {
        "role": "销售/市场/客户成功",
        "keywords": ["销售", "市场", "营销", "客户", "渠道", "谈判", "活动", "新媒体", "转化"],
        "evidence": ["活动策划", "客户沟通", "销售", "社群", "文案", "成交", "满意度"],
        "starter_jd_keywords": ["客户沟通", "活动策划", "线索转化", "数据复盘", "服务意识"],
    },
    {
        "role": "产品/运营/项目助理",
        "keywords": ["产品", "运营", "用户", "需求", "调研", "流程", "项目管理", "数据分析"],
        "evidence": ["用户调研", "活动运营", "流程优化", "项目管理", "数据复盘"],
        "starter_jd_keywords": ["需求分析", "数据分析", "用户反馈", "活动运营", "沟通协调"],
    },
    {
        "role": "技术开发/数据分析",
        "keywords": ["python", "java", "go", "sql", "mysql", "redis", "linux", "算法", "数据分析", "机器学习"],
        "evidence": ["项目", "系统", "开发", "建模", "数据库", "竞赛", "github"],
        "starter_jd_keywords": ["编程语言", "数据库", "项目经验", "问题排查", "数据结构"],
    },
    {
        "role": "制造/质量/供应链",
        "keywords": ["机械", "制造", "质量", "供应链", "采购", "物流", "生产", "cad", "工艺"],
        "evidence": ["现场", "质量", "CAD", "SolidWorks", "工厂", "采购", "仓储"],
        "starter_jd_keywords": ["质量管理", "现场协调", "流程优化", "CAD", "数据统计"],
    },
    {
        "role": "设计/传媒/内容",
        "keywords": ["设计", "视觉", "figma", "photoshop", "剪辑", "视频", "文案", "内容", "作品集"],
        "evidence": ["作品集", "海报", "视频", "公众号", "新媒体", "视觉设计"],
        "starter_jd_keywords": ["作品集", "视觉表达", "按时交付", "协作沟通", "内容策划"],
    },
]


def _text_from_profile(verified: dict | None, resume_text: str = "") -> str:
    if not verified:
        return resume_text.lower()
    resume = verified.get("resume", {})
    parts = [
        resume_text,
        " ".join(resume.get("skills", [])),
        " ".join(str(p.get("name", p)) if isinstance(p, dict) else str(p) for p in resume.get("projects", [])),
        " ".join(str(c) for c in resume.get("certifications", [])),
        " ".join(str(e) for e in resume.get("education", [])),
    ]
    return " ".join(parts).lower()


def plan_targets(resume_text: str = "", verified: dict | None = None) -> dict:
    profile_text = _text_from_profile(verified, resume_text)
    planned = []
    for profile in ROLE_PROFILES:
        keyword_hits = [kw for kw in profile["keywords"] if kw.lower() in profile_text]
        evidence_hits = [kw for kw in profile["evidence"] if kw.lower() in profile_text]
        score = min(95, 38 + len(keyword_hits) * 9 + len(evidence_hits) * 11)
        if keyword_hits or evidence_hits:
            planned.append({
                "role": profile["role"],
                "fit": score,
                "reason": "、".join((keyword_hits + evidence_hits)[:5]) or "画像存在相关信号",
                "evidence": (keyword_hits + evidence_hits)[:6],
                "starter_jd_keywords": profile["starter_jd_keywords"],
            })

    if not planned:
        planned.append({
            "role": "通用管培/行政运营/项目助理",
            "fit": 55,
            "reason": "当前简历可识别信号不足，建议先补充经历、技能和目标行业",
            "evidence": [],
            "starter_jd_keywords": ["沟通协调", "Office", "数据整理", "执行力", "服务意识"],
        })

    planned = sorted(planned, key=lambda item: item["fit"], reverse=True)[:5]
    return {
        "target_roles": planned,
        "positioning_summary": f"优先探索：{planned[0]['role']}；同时保留 {planned[1]['role'] if len(planned) > 1 else '通用岗位'} 作为备选。",
    }


def follow_up_questions(resume_text: str = "", verified: dict | None = None, results: dict | None = None) -> list[dict]:
    text = resume_text or ""
    resume = (verified or {}).get("resume", {})
    diagnostics = (results or {}).get("diagnostics", {})
    questions = []

    def add(qid: str, question: str, reason: str, answer_hint: str):
        if not any(q["id"] == qid for q in questions):
            questions.append({"id": qid, "question": question, "reason": reason, "answer_hint": answer_hint})

    if not resume.get("education") and not re.search(r"本科|硕士|博士|大专|学院|大学", text):
        add("education", "你的学校、专业、学历和毕业时间分别是什么？", "缺少门槛资质信息，很多岗位会先筛学历/专业。", "例：XX大学，会计学，本科，2026届")

    if len(resume.get("projects", [])) < 2:
        add("experience", "还有没有实习、课程项目、社团实践、作品集或兼职经历可以补充？", "经历证据偏少，系统很难判断岗位适配度。", "按“场景-职责-动作-结果”写1-2段即可")

    if not re.search(r"\d+|%|人|次|元|小时|天|周|月", text):
        add("metrics", "你的经历里有没有可量化结果？", "缺少量化结果会削弱简历说服力。", "例：服务30名客户、整理200份凭证、活动到场率提升20%")

    if not resume.get("certifications"):
        add("certification", "目标行业有没有相关证书、资格、语言等级或考试成绩？", "证书/资格是教育、医疗、财会、公职等岗位的重要门槛。", "例：教师资格证、初级会计、英语六级、普通话二甲")

    missing_skills = diagnostics.get("skills", {}).get("missing", [])
    if missing_skills:
        add("jd_gap", f"JD里提到的 {missing_skills[0]}，你是否有学习、课程、证书或实践证据？", "这是当前岗位的关键缺口，确认后可以避免误判。", "如没有，就标记为学习中；如有，补充真实证据")

    soft_evidence = resume.get("soft_evidence", [])
    if len(soft_evidence) < 2:
        add("soft_evidence", "能否补充一次沟通协作、服务对象、组织协调或问题处理的具体案例？", "通用素质需要证据支撑，不能只写空泛评价。", "例：与谁协作、遇到什么问题、你做了什么、结果如何")

    return questions[:6]


def resume_version_preview(resume_text: str, jd_text: str, results: dict) -> dict:
    suggestions = results.get("suggestions", [])[:5]
    strategy = results.get("strategy", {})
    focus = strategy.get("resume_focus", [])
    return {
        "version_name": "目标岗位定制版",
        "target_focus": focus or ["围绕目标JD重排经历顺序", "补充关键能力证据", "强化可量化结果"],
        "rewrite_queue": suggestions,
        "score_snapshot": {
            "overall_score": results.get("overall_score", 0),
            "recommended_action": strategy.get("recommended_action", ""),
        },
        "source_note": "草稿只记录修改方向，不替用户编造经历。",
    }


def agent_chat_response(context: dict, messages: list[dict], user_message: str) -> dict:
    """围绕当前简历/JD/匹配结果进行求职智能体对话。"""
    compact_context = {
        "overall_score": context.get("overall_score"),
        "dimensions": context.get("dimensions"),
        "gap_analysis": context.get("gap_analysis"),
        "strategy": context.get("strategy"),
        "resume_text_excerpt": (context.get("resume_text") or "")[:1200],
        "jd_text_excerpt": (context.get("jd_text") or "")[:1200],
    }
    history = messages[-8:] if messages else []
    system_prompt = """你是OfferCatcher求职智能体。你要基于当前简历、JD、匹配分、差距和投递策略，回答学生关于求职方向、简历优化、岗位选择、补充信息和投递策略的问题。

规则：
- 只基于上下文和用户提供的信息回答，不编造经历。
- 如果信息不足，先指出缺口，并给出1-3个追问。
- 语气像求职顾问，具体、可执行、不要空泛鼓励。
- 不输出面试题或面试准备模块；如果用户问面试，只给简短方向，不展开题库。

输出JSON：
{"answer":"回答正文","suggested_actions":["下一步动作1","下一步动作2"],"needs_more_info":false,"follow_up_questions":["问题1","问题2"]}"""
    user_prompt = {
        "context": compact_context,
        "history": history,
        "user_message": user_message,
    }
    return chat_json(system_prompt, str(user_prompt), temperature=0.4)


def application_insights(db, user_id: str) -> dict:
    apps = (
        db.query(Application, MatchRecord)
        .join(MatchRecord, Application.match_id == MatchRecord.match_id)
        .join(Resume, MatchRecord.resume_id == Resume.resume_id)
        .filter(Resume.user_id == user_id)
        .all()
    )
    rows = []
    for app, match in apps:
        data = match.match_result_json or {}
        rows.append({
            "status": app.status,
            "score": data.get("overall_score", 0),
            "dimensions": data.get("dimensions", {}),
            "feedback": app.feedback_text or "",
        })

    if not rows:
        return {
            "total": 0,
            "conversion": {"interview": 0, "offer": 0, "rejected": 0},
            "recommended_min_score": 75,
            "insight": "还没有投递反馈。先记录3-5次投递结果，系统会开始校准你的投递阈值。",
            "weak_dimensions": [],
        }

    total = len(rows)
    interviews = [r for r in rows if r["status"] in {"interview", "offer"}]
    offers = [r for r in rows if r["status"] == "offer"]
    rejected = [r for r in rows if r["status"] == "rejected"]
    success_scores = [r["score"] for r in interviews if r["score"]]
    rejected_scores = [r["score"] for r in rejected if r["score"]]
    recommended = round(mean(success_scores)) if success_scores else (max(rejected_scores) + 5 if rejected_scores else 75)
    recommended = max(55, min(90, recommended))

    weak_totals = {}
    for row in rejected:
        for key, dim in (row["dimensions"] or {}).items():
            weak_totals.setdefault(key, []).append(dim.get("score", 0))
    weak_dimensions = [
        {"dimension": key, "avg_score": round(mean(vals))}
        for key, vals in weak_totals.items()
        if vals and mean(vals) < 70
    ]
    weak_dimensions = sorted(weak_dimensions, key=lambda item: item["avg_score"])[:4]

    return {
        "total": total,
        "conversion": {
            "interview": round(len(interviews) / total * 100),
            "offer": round(len(offers) / total * 100),
            "rejected": round(len(rejected) / total * 100),
        },
        "recommended_min_score": recommended,
        "insight": f"基于 {total} 条投递反馈，建议优先投递匹配分不低于 {recommended} 的岗位。",
        "weak_dimensions": weak_dimensions,
    }
