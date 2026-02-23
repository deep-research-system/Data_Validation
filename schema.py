from __future__ import annotations

from typing import List, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum





#---------------------------------

# 로직 근거 추출 스키마
#---------------------------------
class EvidenceItem(BaseModel):
    """
    1단계: '근거(raw)'만 뽑아내는 구조.
    - raw는 설문지에 적힌 지시문을 그대로 복사해야 함
    - end_col/mid_col 같은 최종 필드는 여기서 만들지 않음
    """
    start_col: str
    value: List[Union[int, str]]
    raw: str
    kind_hint: Literal["skip", "branch"] = Field(
        description='raw에 "응답 후" 또는 "~만 응답"이 있으면 branch, 아니면 skip'
    )


class EvidenceList(BaseModel):
    items: List[EvidenceItem] = Field(default_factory=list)
    
#---------------------------------
# 로직 판단 스키마
#---------------------------------

class ColumnTitle(str, Enum):
    """
    설문지에서 스킵 로직이 걸리는 문항의 컬럼 제목.
    """
    스킵 = "스킵"
    브랜치스킵 = "브랜치스킵"
    
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

class branch_skip_rule(BaseModel):
    """
    조건 충족 시 중간에 응답해야할 문항 거친뒤 최종 이동하는 규칙.
    """
    type: Literal["branch_skip"] = "branch_skip"
    start_col: str
    value: List[Union[int, str]]
    mid_col: str
    end_col: str
    note: str = Field(default="", description="로직 판단 이유 설명")



RuleType = Union[SkipRule, branch_skip_rule]


# ----------------------------
# Group 구조
# ----------------------------

    
    
class RuleGroup(BaseModel):
    """
    스킵 로직이 동일한 문항 그룹
    """
    start_col: str
    rule: List[RuleType] = Field(default_factory=list)


class ValidationSchema(BaseModel):
    """
    설문지의 스킵 로직 전체 구조
    """
    type: ColumnTitle = Field(description="반드시 '스킵' 또는 '브랜치스킵' 중 하나")
    groups: List[RuleGroup] = Field(default_factory=list)  # default_factory=list : groups 필드가 제공되지 않거나 None인 경우 빈 리스트로 초기화