import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Boolean
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=gen_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Resume(Base):
    __tablename__ = "resumes"

    resume_id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), default="demo_user")
    profile_json = Column(JSON)
    file_url = Column(String(500), nullable=True)
    parsed_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    jd_id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), default="demo_user")
    title = Column(String(200), default="")
    company = Column(String(200), default="")
    raw_text = Column(Text)
    dna_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class MatchRecord(Base):
    __tablename__ = "match_records"

    match_id = Column(String(36), primary_key=True, default=gen_uuid)
    resume_id = Column(String(36), ForeignKey("resumes.resume_id"))
    jd_id = Column(String(36), ForeignKey("job_descriptions.jd_id"))
    match_result_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Application(Base):
    __tablename__ = "applications"

    app_id = Column(String(36), primary_key=True, default=gen_uuid)
    match_id = Column(String(36), ForeignKey("match_records.match_id"))
    status = Column(String(20), default="pending")
    feedback_text = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    version_id = Column(String(36), primary_key=True, default=gen_uuid)
    resume_id = Column(String(36), ForeignKey("resumes.resume_id"))
    jd_id = Column(String(36), ForeignKey("job_descriptions.jd_id"), nullable=True)
    match_id = Column(String(36), ForeignKey("match_records.match_id"), nullable=True)
    name = Column(String(120), default="目标岗位定制版")
    target_role = Column(String(120), default="")
    content_json = Column(JSON)
    score_snapshot = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
