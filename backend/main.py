"""
OfferCatcher MVP — FastAPI 主应用
"""
import io
import logging
import os
import hashlib
import secrets
from datetime import datetime, timedelta

import jwt
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

import pdfplumber
from docx import Document

from database import init_db, get_db, SessionLocal
from models.db_models import User, Resume, JobDescription, MatchRecord, ResumeVersion
from services.extractor import extract
from services.verifier import verify_extraction
from services.scorer import score
from services.narrator import narrate
from services.career_agent import (
    agent_chat_response,
    application_insights,
    follow_up_questions,
    plan_targets,
    resume_version_preview,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing (using hashlib, zero external dependencies)
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"

def verify_password(password: str, hashed: str) -> bool:
    salt, h = hashed.split("$", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == h

SECRET_KEY = os.getenv("JWT_SECRET", "offer-catcher-secret-key-change-in-prod")
ALGORITHM = "HS256"


def create_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(authorization: str = Header(None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(401, "用户不存在")
            return user
        finally:
            db.close()
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "登录已过期")
    except jwt.PyJWTError:
        raise HTTPException(401, "无效的登录凭证")


app = FastAPI(title="OfferCatcher MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    # 自动创建 admin 用户
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                hashed_password=hash_password("admin"),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Admin user created: admin/admin")
    finally:
        db.close()
    logger.info("Database initialized")


# === 用户认证 ===

@app.post("/api/register")
def register(req: dict, db: Session = Depends(get_db)):
    """注册新用户"""
    username = (req.get("username") or "").strip()
    password = (req.get("password") or "").strip()
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")
    if len(username) < 2 or len(password) < 3:
        raise HTTPException(400, "用户名至少2位，密码至少3位")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "用户名已存在")
    user = User(
        username=username,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.user_id, user.username)
    return {"token": token, "user_id": user.user_id, "username": user.username}


@app.post("/api/login")
def login(req: dict, db: Session = Depends(get_db)):
    """用户登录"""
    username = (req.get("username") or "").strip()
    password = (req.get("password") or "").strip()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        logger.warning(f"LOGIN FAIL: user '{username}' not found")
        raise HTTPException(401, "用户名或密码错误")
    if not verify_password(password, user.hashed_password):
        logger.warning(f"LOGIN FAIL: password mismatch for '{username}' (hash={user.hashed_password[:20]}...)")
        raise HTTPException(401, "用户名或密码错误")
    logger.info(f"LOGIN OK: {username}")
    token = create_token(user.user_id, user.username)
    return {"token": token, "user_id": user.user_id, "username": user.username, "is_admin": user.is_admin}


@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {"user_id": user.user_id, "username": user.username, "is_admin": user.is_admin}


@app.get("/api/health")
def health():
    """健康检查"""
    from config import get_provider_config
    cfg = get_provider_config()
    return {
        "status": "ok",
        "provider": cfg["name"],
        "model": cfg["model"],
    }


@app.get("/api/test-llm")
def test_llm():
    """测试 LLM 连通性：发一个简单请求验证 API Key 和网络"""
    from services.llm_client import chat_json
    try:
        result = chat_json(
            "你是一个测试助手，请只返回 JSON。",
            "请返回 {\"hello\": \"world\", \"time\": \"now\"}"
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/test-llm-medium")
def test_llm_medium():
    """测试中等负载：模拟 ~1500 字输入，验证是否阈值超时"""
    from services.llm_client import chat_json
    fake_resume = (
        "张三，男，24岁，计算机科学与技术专业本科。"
        "熟练掌握 Python、Java、C++，熟悉 MySQL、Redis、Docker。"
        "项目经历：1) 分布式 RPC 框架，基于 Netty+Zookeeper，QPS 达 5W。"
        "2) 即时通讯系统，支持万人同时在线。3) AI Agent 项目 LiaoClaw。"
        "竞赛：蓝桥杯省一等奖、ACM-ICPC 区域赛铜牌。英语六级。"
    ) * 5  # 重复5次 → ~1500 字
    try:
        result = chat_json(
            "你是一个简历解析器。请将以下文本解析为 JSON，包含 name、skills、projects 字段。",
            f"请解析以下简历：\n{fake_resume}"
        )
        return {"status": "ok", "len": len(fake_resume), "result": result}
    except Exception as e:
        return {"status": "error", "len": len(fake_resume), "detail": str(e)}


# === 简历上传 & 解析 ===

@app.post("/api/extract-text")
async def extract_text(file: UploadFile = File(...)):
    """纯文本提取：上传 PDF/Word，返回原始文字，不调用 LLM"""
    content = await file.read()
    filename = file.filename or ""
    text = ""
    try:
        if filename.lower().endswith(".pdf"):
            # 优先 PyMuPDF（中文 PDF 效果更好），fallback pdfplumber
            try:
                import fitz
                with fitz.open(stream=content, filetype="pdf") as doc:
                    pages = []
                    for page in doc:
                        # sort=True 按阅读顺序排列文本块
                        t = page.get_text("text", sort=True)
                        if t:
                            pages.append(t)
                    text = "\n".join(pages)
            except ImportError:
                pass  # fallback below

            # Fallback：pdfplumber
            if not text or len(text.strip()) < 100:
                with io.BytesIO(content) as f:
                    with pdfplumber.open(f) as pdf:
                        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        elif filename.lower().endswith((".docx", ".doc")):
            with io.BytesIO(content) as f:
                doc = Document(f)
                text = "\n".join(p.text for p in doc.paragraphs)
        else:
            raise HTTPException(400, "仅支持 PDF 和 Word (.docx) 格式")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, f"文件解析失败: {str(e)}")

    if not text or len(text.strip()) < 50:
        raise HTTPException(422, "简历文本内容过少")
    logger.info(f"Text extracted: {len(text)} chars")
    return {"text": text, "length": len(text), "filename": filename}


@app.post("/api/analyze", response_model=dict)

@app.post("/api/analyze", response_model=dict)
async def api_analyze_deprecated():
    """已废弃，请使用 POST /api/analyze-v2（LLM提取→代码验证→代码评分→LLM文案）"""
    raise HTTPException(410, "此接口已废弃，请使用 POST /api/analyze-v2")

# === 一站式分析 V2（推荐） ===


@app.post("/api/analyze-v2")
async def api_analyze_v2(req: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """可靠引擎：LLM提取 → 代码验证 → 代码评分 → LLM文案"""
    resume_text = (req.get("resume_text") or "").strip()
    jd_text = (req.get("jd_text") or "").strip()
    filename = (req.get("filename") or "简历").strip()

    if len(resume_text) < 50:
        raise HTTPException(400, "简历文本过短")
    if len(jd_text) < 30:
        raise HTTPException(400, "JD文本过短")

    # Step 1: LLM 提取结构化数据
    extracted = extract(resume_text, jd_text)

    # Step 2: 代码反向验证，剔除幻觉
    verified = verify_extraction(extracted, resume_text, jd_text)

    # Step 3: 确定性评分
    results = score(verified)

    # Step 4: LLM 生成文案描述
    results = narrate(verified, results)

    # Step 5: 求职智能体策略层
    version_preview = resume_version_preview(resume_text, jd_text, results)

    # 落库
    profile_json = {"resume_text": resume_text, "verified_data": verified, "scores": results.get("dimensions")}
    resume = Resume(user_id=user.user_id, profile_json=profile_json, file_url=filename)
    db.add(resume)
    db.flush()

    jd = JobDescription(user_id=user.user_id, raw_text=jd_text, dna_json=verified["jd"])
    db.add(jd)
    db.flush()

    match_data = {
        "overall_score": results["overall_score"],
        "dimensions": results["dimensions"],
        "gap_analysis": results.get("gap_analysis", []),
        "suggestions": results.get("suggestions", []),
        "match_verdict": results.get("match_verdict", ""),
        "killer_sentence": results.get("killer_sentence", ""),
        "competitive_advantage": results.get("competitive_advantage", ""),
        "interview_probability": results.get("interview_probability", ""),
        "strategy": results.get("strategy", {}),
        "diagnostics": results.get("diagnostics", {}),
        "resume_version_preview": version_preview,
    }
    record = MatchRecord(resume_id=resume.resume_id, jd_id=jd.jd_id, match_result_json=match_data)
    db.add(record)
    db.commit()

    return {
        "resume_id": resume.resume_id,
        "jd_id": jd.jd_id,
        "match_id": record.match_id,
        "verified": verified,
        "resume_version_preview": version_preview,
        **results,
    }


# === 历史分析记录 ===

@app.get("/api/match-history")
def match_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户的所有历史分析记录"""
    records = (
        db.query(MatchRecord, Resume, JobDescription)
        .join(Resume, MatchRecord.resume_id == Resume.resume_id)
        .join(JobDescription, MatchRecord.jd_id == JobDescription.jd_id)
        .filter(Resume.user_id == user.user_id, Resume.deleted_at.is_(None))
        .order_by(MatchRecord.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "history": [{
            "match_id": m.match_id,
            "resume_id": m.resume_id,
            "resume_name": r.file_url or "简历",
            "jd_title": j.title or "JD",
            "jd_snippet": (j.raw_text or "")[:80].replace("\n", " "),
            "overall_score": (m.match_result_json or {}).get("overall_score"),
            "match_verdict": (m.match_result_json or {}).get("match_verdict", ""),
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m, r, j in records]
    }


@app.get("/api/match/{match_id}")
def get_match(match_id: str, db: Session = Depends(get_db)):
    """获取单次匹配的完整记录"""
    match = db.query(MatchRecord).filter(MatchRecord.match_id == match_id).first()
    if not match:
        raise HTTPException(404, "匹配记录不存在")
    jd = db.query(JobDescription).filter(JobDescription.jd_id == match.jd_id).first()
    resume = db.query(Resume).filter(Resume.resume_id == match.resume_id).first()
    return {
        "match_id": match.match_id,
        "resume_id": match.resume_id,
        "resume_text": (resume.profile_json or {}).get("resume_text", "") if resume else "",
        "jd_id": match.jd_id,
        "jd_text": jd.raw_text if jd else "",
        "overall_score": (match.match_result_json or {}).get("overall_score"),
        "dimensions": (match.match_result_json or {}).get("dimensions"),
        "gap_analysis": (match.match_result_json or {}).get("gap_analysis", []),
        "suggestions": (match.match_result_json or {}).get("suggestions", []),
        "match_verdict": (match.match_result_json or {}).get("match_verdict", ""),
        "killer_sentence": (match.match_result_json or {}).get("killer_sentence", ""),
        "strategy": (match.match_result_json or {}).get("strategy"),
        "created_at": match.created_at.isoformat() if match.created_at else None,
    }


# === 求职智能体扩展能力 ===

@app.post("/api/agent/plan-targets")
def api_plan_targets(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """根据学生画像/简历文本推荐适合的岗位方向"""
    resume_text = (req.get("resume_text") or "").strip()
    resume_id = req.get("resume_id")
    verified = req.get("verified")
    if resume_id and not resume_text:
        resume = db.query(Resume).filter(Resume.resume_id == resume_id, Resume.user_id == user.user_id).first()
        if not resume:
            raise HTTPException(404, "简历不存在")
        profile = resume.profile_json or {}
        resume_text = profile.get("resume_text", "")
        verified = profile.get("verified_data")
    if len(resume_text) < 20 and not verified:
        raise HTTPException(400, "请先提供简历文本或已解析画像")
    return plan_targets(resume_text, verified)


@app.post("/api/agent/follow-up-questions")
def api_follow_up_questions(req: dict, user: User = Depends(get_current_user)):
    """发现简历信息不足时，生成多轮追问问题"""
    resume_text = (req.get("resume_text") or "").strip()
    verified = req.get("verified")
    results = req.get("results")
    return {"questions": follow_up_questions(resume_text, verified, results)}


@app.get("/api/match-record/{match_id}")
def get_match_record(match_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """读取单次匹配分析结果，用于独立分析页刷新恢复"""
    record = db.query(MatchRecord).filter(MatchRecord.match_id == match_id).first()
    if not record:
        raise HTTPException(404, "匹配记录不存在")
    resume = db.query(Resume).filter(Resume.resume_id == record.resume_id, Resume.user_id == user.user_id).first()
    jd = db.query(JobDescription).filter(JobDescription.jd_id == record.jd_id, JobDescription.user_id == user.user_id).first()
    if not resume or not jd:
        raise HTTPException(404, "关联简历或JD不存在")
    data = record.match_result_json or {}
    return {
        "resume_id": record.resume_id,
        "jd_id": record.jd_id,
        "match_id": record.match_id,
        "resume_text": (resume.profile_json or {}).get("resume_text", ""),
        "jd_text": jd.raw_text or "",
        "verified": (resume.profile_json or {}).get("verified_data"),
        **data,
    }


@app.post("/api/agent/chat")
def api_agent_chat(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """与求职智能体对话"""
    message = (req.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "消息不能为空")

    context = req.get("context") or {}
    match_id = req.get("match_id")
    if match_id:
        record = db.query(MatchRecord).filter(MatchRecord.match_id == match_id).first()
        if not record:
            raise HTTPException(404, "匹配记录不存在")
        resume = db.query(Resume).filter(Resume.resume_id == record.resume_id, Resume.user_id == user.user_id).first()
        jd = db.query(JobDescription).filter(JobDescription.jd_id == record.jd_id, JobDescription.user_id == user.user_id).first()
        if not resume or not jd:
            raise HTTPException(404, "关联简历或JD不存在")
        context = {
            **(record.match_result_json or {}),
            "resume_text": (resume.profile_json or {}).get("resume_text", ""),
            "jd_text": jd.raw_text or "",
        }

    try:
        return agent_chat_response(context, req.get("messages") or [], message)
    except Exception as e:
        raise HTTPException(500, f"智能体回复失败: {str(e)}")


@app.get("/api/application-insights")
def api_application_insights(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """汇总投递反馈，反向校准投递阈值和薄弱维度"""
    return application_insights(db, user.user_id)


@app.post("/api/resume-versions")
def create_resume_version(req: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """保存某个目标岗位的简历版本草稿/修改队列"""
    resume_id = req.get("resume_id")
    if not resume_id:
        raise HTTPException(400, "resume_id不能为空")
    resume = db.query(Resume).filter(Resume.resume_id == resume_id, Resume.user_id == user.user_id).first()
    if not resume:
        raise HTTPException(404, "简历不存在")

    version = ResumeVersion(
        resume_id=resume_id,
        jd_id=req.get("jd_id"),
        match_id=req.get("match_id"),
        name=req.get("name") or "目标岗位定制版",
        target_role=req.get("target_role") or "",
        content_json=req.get("content_json") or {},
        score_snapshot=req.get("score_snapshot") or {},
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return {
        "version_id": version.version_id,
        "resume_id": version.resume_id,
        "name": version.name,
        "target_role": version.target_role,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@app.get("/api/resume-versions")
def list_resume_versions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """查看当前用户的简历版本历史"""
    rows = (
        db.query(ResumeVersion)
        .join(Resume, ResumeVersion.resume_id == Resume.resume_id)
        .filter(Resume.user_id == user.user_id, Resume.deleted_at.is_(None))
        .order_by(ResumeVersion.created_at.desc())
        .all()
    )
    return {
        "versions": [{
            "version_id": row.version_id,
            "resume_id": row.resume_id,
            "jd_id": row.jd_id,
            "match_id": row.match_id,
            "name": row.name,
            "target_role": row.target_role,
            "content_json": row.content_json,
            "score_snapshot": row.score_snapshot,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        } for row in rows]
    }


# === 数据安全与隐私管理 ===

# === 简历管理 ===

@app.get("/api/resumes")
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户已保存的简历列表"""
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == user.user_id, Resume.deleted_at.is_(None))
        .order_by(Resume.parsed_at.desc())
        .all()
    )
    return {
        "resumes": [{
            "resume_id": r.resume_id,
            "filename": r.file_url or "未命名简历",
            "parsed_at": r.parsed_at.isoformat() if r.parsed_at else None,
            "summary": (r.profile_json or {}).get("summary", ""),
            "skills_count": len((r.profile_json or {}).get("skills", {}).get("hard_skills", [])),
        } for r in resumes]
    }


@app.get("/api/resume/{resume_id}")
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    """获取指定简历的完整信息 + 最后一次分析结果"""
    resume = db.query(Resume).filter(Resume.resume_id == resume_id).first()
    if not resume:
        raise HTTPException(404, "简历不存在")

    # 查最后一次匹配记录
    latest_match = (
        db.query(MatchRecord)
        .filter(MatchRecord.resume_id == resume_id)
        .order_by(MatchRecord.created_at.desc())
        .first()
    )

    match_data = None
    if latest_match:
        jd = db.query(JobDescription).filter(JobDescription.jd_id == latest_match.jd_id).first()
        match_data = {
            "match_id": latest_match.match_id,
            "jd_id": latest_match.jd_id,
            "jd_text": jd.raw_text if jd else "",
            "overall_score": latest_match.match_result_json.get("overall_score"),
            "dimensions": latest_match.match_result_json.get("dimensions"),
            "match_verdict": latest_match.match_result_json.get("match_verdict"),
            "killer_sentence": latest_match.match_result_json.get("killer_sentence"),
            "gap_analysis": latest_match.match_result_json.get("gap_analysis", []),
            "suggestions": latest_match.match_result_json.get("suggestions", []),
            "created_at": latest_match.created_at.isoformat() if latest_match.created_at else None,
        }

    return {
        "resume_id": resume.resume_id,
        "resume_text": (resume.profile_json or {}).get("resume_text", ""),
        "profile_json": resume.profile_json,
        "last_analysis": match_data,
    }


@app.get("/api/data-summary")
def data_summary(db: Session = Depends(get_db)):
    """查看当前存储的数据概要"""
    resume_count = db.query(Resume).filter(Resume.deleted_at.is_(None)).count()
    jd_count = db.query(JobDescription).count()
    match_count = db.query(MatchRecord).count()
    app_count = db.query(Application).count()
    return {
        "resumes": resume_count,
        "job_descriptions": jd_count,
        "match_records": match_count,
        "applications": app_count,
        "note": "所有数据仅存储在本地 SQLite，不上传任何服务器"
    }


@app.delete("/api/resume/{resume_id}")
def delete_resume(resume_id: str, db: Session = Depends(get_db)):
    """软删除指定简历及其关联数据（可恢复）"""
    from datetime import datetime

    resume = db.query(Resume).filter(Resume.resume_id == resume_id).first()
    if not resume:
        raise HTTPException(404, "简历记录不存在")

    # 软删除简历
    resume.deleted_at = datetime.utcnow()

    # 删除关联的匹配记录
    db.query(MatchRecord).filter(MatchRecord.resume_id == resume_id).delete()

    db.commit()
    return {"status": "deleted", "resume_id": resume_id, "note": "已软删除，30天后物理清除"}


@app.delete("/api/all-data")
def delete_all_data(db: Session = Depends(get_db)):
    """清空所有数据"""
    # 按外键依赖顺序删除，用原生 SQL 避免 SQLAlchemy JOIN 问题
    db.execute(text("DELETE FROM applications"))
    db.execute(text("DELETE FROM resume_versions"))
    db.execute(text("DELETE FROM match_records"))
    db.execute(text("DELETE FROM job_descriptions"))
    db.execute(text("DELETE FROM resumes"))
    db.commit()
    return {"status": "cleared", "note": "所有数据已物理删除，不可恢复"}


# === 生产模式：服务前端（SPA 路由支持） ===
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(FRONTEND_DIR):
    from fastapi.responses import FileResponse

    # 挂载静态资源（JS/CSS/图片等）
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback：所有非 API 路径返回 index.html"""
        if full_path.startswith("api/"):
            raise HTTPException(404, "API route not found")
        file_path = os.path.join(FRONTEND_DIR, full_path) if full_path else FRONTEND_DIR
        if os.path.isfile(file_path) and not full_path.startswith("api/"):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
