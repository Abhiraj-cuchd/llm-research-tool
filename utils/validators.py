from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class DimensionConfig(BaseModel):
    id: str
    label: str
    weight: float
    description: str


class Codebook(BaseModel):
    version: str
    scale: int
    dimensions: list[DimensionConfig]
    prompt_template: str


class LLMConfig(BaseModel):
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"

    @field_validator("api_key")
    @classmethod
    def api_key_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("API key must not be empty")
        return v.strip()


class DimensionScore(BaseModel):
    score: int
    confidence: float
    evidence: list[str]
    reason: str

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    @field_validator("score")
    @classmethod
    def score_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("score must be non-negative")
        return v


class CodingResult(BaseModel):
    participant: str
    dimensions: dict[str, DimensionScore]
    model: str
    prompt_version: str
    timestamp: str
    summary: str = ""
    human_reviewed: bool = False


class FailedCoding(BaseModel):
    participant: str
    error: str
    raw_output: str = ""


class ParticipantScore(BaseModel):
    participant: str
    dimension_scores: dict[str, float]
    overall: float


class RunMetadata(BaseModel):
    model: str
    timestamp: str
    prompt_version: str
    codebook_version: str
    participant_count: int = 0
    completed_count: int = 0
    failed_count: int = 0


class InterviewJSON(BaseModel):
    participant: str
    questions: list[dict]
