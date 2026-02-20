from __future__ import annotations

from typing import List, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ColumnTitle(str, Enum):
    """
    설문지에서 스킵 로직이 걸리는 문항의 컬럼 제목.
    """
    스킵 = "스킵"
    
# ----------------------------
# Rule 정의
# ----------------------------

class SkipRule(BaseModel):
    """
    스킵 로직(조건부 문항 이동) 규칙.
    """
    type: Literal["skip"] = "skip"
    start_col: str
    value: List[Union[int, str]]    
    end_col: str
    note: str = Field(default="", description="로직 판단 이유 설명")

RuleType = Union[SkipRule]


# ----------------------------
# Group 구조
# ----------------------------

    
    
class RuleGroup(BaseModel):
    """
    스킵 로직이 동일한 문항 그룹
    """
    items: List[str]
    rule: RuleType


class ValidationSchema(BaseModel):
    """
    설문지의 스킵 로직 전체 구조
    """
    type: ColumnTitle = Field(description="반드시 \"스킵\" 중 하나")
    groups: List[RuleGroup] = Field(default_factory=list)  # default_factory=list : groups 필드가 제공되지 않거나 None인 경우 빈 리스트로 초기화