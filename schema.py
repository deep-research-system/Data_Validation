from __future__ import annotations

from enum import Enum
from typing import List, Union, Literal, Optional
from pydantic import BaseModel, Field


# ----------------------------
# 공통 타입
# ----------------------------
AnswerValue = Union[int, str]


class RuleKind(str, Enum):
    skip = "skip"


# ----------------------------
# Rule 정의
# ----------------------------
class BaseRule(BaseModel):
    """
    모든 로직 규칙의 공통 필드
    """
    type: RuleKind
    start_col: str
    value: List[AnswerValue] = Field(default_factory=list)

    # 근거(원문 지시문)
    raw: Optional[str] = Field(default=None, description="설문지에 적힌 지시문 원문(가능하면 그대로)")
    note: str = Field(default="", description="로직 판단 이유/보완 설명")


class SkipRule(BaseRule):
    """
    조건 충족 시 특정 문항으로 즉시 이동
    예) (문3-1) ② 없음 ☞ 3-2로 이동
    """
    type: Literal[RuleKind.skip] = RuleKind.skip
    end_col: str



RuleType = Union[SkipRule]


# ----------------------------
# Group 구조
# ----------------------------
class RuleGroup(BaseModel):
    """
    start_col(출발 문항) 기준으로 규칙 묶음
    """
    start_col: str
    rules: List[RuleType] = Field(default_factory=list)


class ValidationSchema(BaseModel):
    """
    설문지 전체 로직 구조
    """
    groups: List[RuleGroup] = Field(default_factory=list)