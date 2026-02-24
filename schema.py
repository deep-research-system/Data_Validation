from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class LogicCandidate(BaseModel):
    type: Literal["candidate"] = "candidate"
    page: Optional[int] = None           # 있으면 좋고 없어도 됨
    line_no: Optional[int] = None        # 있으면 좋고 없어도 됨
    start_hint: str = ""                 # 후보가 속한 문항ID 추정(없으면 "")
    raw: str                              # 후보 문장(원문 그대로)
    context_prev: str = ""                # 바로 위 1~2줄
    context_next: str = ""                # 바로 아래 1~2줄
    reason: str = ""                      # 왜 후보인지(키워드/기호 매칭 등)
    
    
    @field_validator("context_prev", "context_next", "start_hint", "reason", mode="before")
    @classmethod
    def none_to_empty(cls, v):
        return "" if v is None else v

class LogicCandidates(BaseModel):
    items: List[LogicCandidate] = Field(default_factory=list)
    
    
class SkipRule(BaseModel):
    """단일 선택값 기반 스킵/이동 규칙"""
    type: Literal["skip"] = "skip"
    start: str               # 문항ID (예: Q2-1, A4)
    value: str               # 단일값만 (예: "2")
    end: str                 # 이동 대상 문항ID (예: A39, A4-1)
    raw: str = ""            #  원문 근거
    note: str = ""           # 추가 설명/판단 근거


class ValidationSchema(BaseModel):
    """전체 결과"""
    rules: List[SkipRule] = Field(default_factory=list)