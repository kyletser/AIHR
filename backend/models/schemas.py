from pydantic import BaseModel
from typing import Optional


# === Request Schemas ===

class JDDecodeRequest(BaseModel):
    jd_text: str


class MatchRequest(BaseModel):
    resume_id: str
    jd_id: str


class OptimizeRequest(BaseModel):
    resume_id: str
    jd_id: str


class TrackRequest(BaseModel):
    match_id: str
    status: str  # pending / interview / offer / rejected
    feedback_text: str = ""


# === Response Schemas ===

class ParseResumeResponse(BaseModel):
    resume_id: str
    profile_json: dict
    parse_status: str


class JDDecodeResponse(BaseModel):
    jd_id: str
    dna_json: dict
    decode_status: str


class MatchResponse(BaseModel):
    match_id: str
    overall_score: int
    dimensions: dict
    gap_analysis: list[dict]


class OptimizationSuggestion(BaseModel):
    section: str
    field: str
    original: str
    suggested: str
    reason: str


class OptimizeResponse(BaseModel):
    resume_id: str
    jd_id: str
    suggestions: list[OptimizationSuggestion]


class TrackResponse(BaseModel):
    app_id: str
    status: str
    insights: Optional[dict] = None
