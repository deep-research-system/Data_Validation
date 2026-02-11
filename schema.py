from __future__ import annotations

from typing import List, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ColumnTitle(str, Enum):
    결측 = "결측"
    중복응답 = "중복응답"
    범위 = "범위"
    스킵 = "스킵"
    
# ----------------------------
# Rule 정의
# ----------------------------

class EmptyRule(BaseModel):
    type: Literal["empty"] = "empty"
    kind: Literal["결측", "중복응답"]
    pass


class RangeRule(BaseModel):
    type: Literal["range"] = "range"
    range_min: int
    range_max: int


class SkipRule(BaseModel):
    type: Literal["skip"] = "skip"
    start_col: str
    value: List[Union[int, str]]    
    end_col: str


RuleType = Union[EmptyRule, RangeRule, SkipRule]


# ----------------------------
# Group 구조
# ----------------------------

    
    
class RuleGroup(BaseModel):
    items: List[str]
    rule: RuleType


class Column(BaseModel):
    title: ColumnTitle
    groups: List[RuleGroup] = Field(default_factory=list)


class ValidationSchema(BaseModel):
    columns: List[Column] = Field(default_factory=list)
