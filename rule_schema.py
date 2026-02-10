# rule_schema.py
from __future__ import annotations

from typing import TypedDict, Literal, Dict, List, Union, Optional, Any, NotRequired


# ---- 기본 리터럴(규칙 타입 / 소스) ----
RuleType = Literal[
    "miss_value",
    "between_a_b",
    "multiple_response_check",
    "early_end",
    "skip_pattern",
    "comparison_columns",
    "comparison_value",
    "require_missing",
    "require_value",
    "conditional_mapping",
    "comparison", 
    "exclusive_multi_value"
]

RuleSource = Literal["codebook", "llm", "manual"]

DTypeHint = Literal["categorical", "numeric", "text", "unknown"]


# ---- 최소 조건 표현 (지금은 optional로만 열어둠) ----
# required_if / skip 같은 조건부 규칙 들어올 때 확장해서 쓰면 됨
class Condition(TypedDict, total=False):
    left: str
    op: Literal["==", "!=", "in", "not_in", ">", ">=", "<", "<="]
    right: Any


# ---- type_hints ----
class TypeHints(TypedDict, total=False):
    dtype: DTypeHint
    multi: bool


# ---- domain ----
class Domain(TypedDict, total=False):
    # codebook에서 파싱되는 허용 코드 집합
    allowed_codes: List[Union[int, str]]

    # (선택) 코드-라벨 매핑: 디버깅/리포트에 유용
    code_label_map: Dict[str, str]


# ---- rule ----
class Rule(TypedDict, total=False):
    rule_id: str                      # 권장: 병합/업데이트/중복 제거에 필요
    rule_type: RuleType

    source: RuleSource
    confidence: float

    # rule payload(최소)
    # allowed_values면 allowed_values가 들어가도 되고(명시형),
    # 아니면 domain.allowed_codes를 사용하도록 엔진에서 해도 됨(암시형).
    allowed_values: NotRequired[List[Union[int, str]]]

    # range 규칙 대비(나중 확장)
    min: NotRequired[Optional[float]]
    max: NotRequired[Optional[float]]
    inclusive_min: NotRequired[bool]
    inclusive_max: NotRequired[bool]

    # 조건부 규칙 대비(나중 확장)
    condition: NotRequired[Condition]

    # (선택) 사람이 읽기 위한 설명
    description: NotRequired[str]


# ---- item spec ----
class ItemSpec(TypedDict, total=False):
    item: str
    type_hints: TypeHints
    domain: Domain
    rules: List[Rule]


# ---- root ----
class RulesJson(TypedDict, total=False):
    version: str
    items: List[ItemSpec]

    # (선택) 메타데이터
    metadata: Dict[str, Any]
