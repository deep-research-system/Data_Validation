from __future__ import annotations

import json
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from schema import ValidationSchema  
from schema import EvidenceList  


load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

TEXT_PATH = Path("output/요양시설_중상.txt")

OUT_EVIDENCE_JSON = Path("output/step1_evidence.json")
OUT_SCHEMA_JSON = Path("output/step2_schema.json")


def run_step1_extract_evidence(text: str) -> EvidenceList:
    """
    1단계: 설문지 전체 텍스트 -> (start_col, value, raw, kind_hint)만 추출
    """
    parser1 = PydanticOutputParser(pydantic_object=EvidenceList)
    fmt1 = parser1.get_format_instructions()

    system_prompt_1 = f"""
너는 설문지 텍스트에서 "문항ID로 이동하는 단순 스킵(skip) 지시문"만 추출하는 엔진이다.


━━━━━━━━━━━━━━━━━━━━
[출력 규칙]
━━━━━━━━━━━━━━━━━━━━

- 출력은 JSON만.
- 아래 스키마(EvidenceList)를 정확히 따른다.
- raw는 설문지에 적힌 지시문을 그대로 복사한다.
- start_col은 해당 지시문이 속한 현재 문항ID이다.
- value는 선택지 번호(①=1, ②=2, ③=3 …)가 명확히 매칭될 때만 채운다.
- 매칭이 불명확하면 value는 [] 로 둔다. (추론 금지)

━━━━━━━━━━━━━━━━━━━━
[Evidence로 인정되는 조건 — 매우 엄격]
━━━━━━━━━━━━━━━━━━━━

raw는 반드시 아래 조건을 모두 만족해야 한다.

1 문항ID로의 "이동 의미"가 명확해야 한다.
   - "로 이동"
   - "으로 이동"
   - "→"
   - "☞"
   단, 반드시 이동 대상 문항ID가 함께 있어야 한다.

2 이동 대상이 반드시 "문항ID"여야 한다.
   문항ID 패턴 예:
   - 문14
   - 문14-4
   - Q12
   - Q12-1
   - B1
   - 3-1-1
   - 숫자-숫자(-숫자)*

3 raw 안에 이동 대상 문항ID가 실제로 존재해야 한다.

━━━━━━━━━━━━━━━━━━━━
[절대 제외]
━━━━━━━━━━━━━━━━━━━━

다음은 절대 추출하지 마라.

- 응답 후 / ~만 응답 (branch 전용이므로 제외)
- 모두 표시
- 하위 보기 안내
- 병설 기관 유형 표시
- 괄호 안 하위 선택지 설명
- 단순 안내/설명 문장
- 이동 대상 문항ID가 없는 ☞ 문장

☞ 가 있어도, 이동 대상 문항ID가 없으면 절대 추출하지 마라.

━━━━━━━━━━━━━━━━━━━━
[kind_hint]
━━━━━━━━━━━━━━━━━━━━

- 모든 항목은 kind_hint="skip"으로 설정한다.

━━━━━━━━━━━━━━━━━━━━
[스키마]
━━━━━━━━━━━━━━━━━━━━
{fmt1}
━━━━━━━━━━━━━━━━━━━━
"""

    messages = [
        SystemMessage(content=system_prompt_1),
        HumanMessage(content=f"설문지 원문 텍스트:\n\n{text}"),
    ]

    raw = llm.invoke(messages).content
    try:
        return parser1.parse(raw)
    except OutputParserException:
        print("[STEP1] 파싱 실패. 원문 응답(raw):")
        print(raw)
        raise


def run_step2_build_schema(evidence: EvidenceList) -> ValidationSchema:
    """
    2단계: 1단계 Evidence만 입력 -> 최종 ValidationSchema로 변환
    (설문지 원문 전체를 다시 주지 않는다: 추론 방지)
    """
    parser2 = PydanticOutputParser(pydantic_object=ValidationSchema)
    fmt2 = parser2.get_format_instructions()

    system_prompt_2 = f"""
너는 1단계에서 추출된 EvidenceList(JSON)만을 사용하여
최종 ValidationSchema로 변환하는 엔진이다.


━━━━━━━━━━━━━━━━━━━━
[절대 규칙]
━━━━━━━━━━━━━━━━━━━━

- 입력 EvidenceList만 사용한다.
- 설문 원문을 추론하지 않는다.
- rule.type은 항상 "skip"이다.
- mid_col은 생성하지 않는다.

━━━━━━━━━━━━━━━━━━━━
[end_col 추출 규칙]
━━━━━━━━━━━━━━━━━━━━

- raw 문자열에서 "이동 대상 문항ID"를 정확히 추출한다.
- 문항ID 패턴:
  - 문14
  - 문14-4
  - Q12
  - Q12-1
  - B1-2
  - 3-1-1
- "~" 범위가 있는 경우 (예: 문14-1~문14-3)
  → 첫 번째 문항ID만 end_col로 사용한다.
    예: 문14-1~문14-3 → end_col="문14-1"

━━━━━━━━━━━━━━━━━━━━
[value 처리]
━━━━━━━━━━━━━━━━━━━━

- Evidence.value가 있으면 그대로 복사
- 없으면 [] 유지
- 절대 추론하지 마라

━━━━━━━━━━━━━━━━━━━━
[grouping]
━━━━━━━━━━━━━━━━━━━━

- start_col 기준으로 groups를 만든다.
- 같은 start_col은 하나의 group으로 묶는다.
- rule.type은 항상 "skip"

━━━━━━━━━━━━━━━━━━━━
[note]
━━━━━━━━━━━━━━━━━━━━

- note는 raw를 기반으로 짧게 작성한다.
- 의역하지 말 것.

━━━━━━━━━━━━━━━━━━━━
[스키마]
━━━━━━━━━━━━━━━━━━━━
{fmt2}
━━━━━━━━━━━━━━━━━━━━

출력은 JSON만.
"""

    evidence_json = json.dumps(evidence.model_dump(), ensure_ascii=False, indent=2)

    messages = [
        SystemMessage(content=system_prompt_2),
        HumanMessage(content=f"1단계 근거 JSON(EvidenceList):\n\n{evidence_json}"),
    ]

    raw = llm.invoke(messages).content
    try:
        return parser2.parse(raw)
    except OutputParserException:
        print("[STEP2] 파싱 실패. 원문 응답(raw):")
        print(raw)
        raise


def main() -> None:
    text = TEXT_PATH.read_text(encoding="utf-8")

    # STEP 1
    evidence = run_step1_extract_evidence(text)
    OUT_EVIDENCE_JSON.write_text(
        json.dumps(evidence.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] step1 evidence saved: {OUT_EVIDENCE_JSON}")

    # STEP 2
    schema_obj = run_step2_build_schema(evidence)
    OUT_SCHEMA_JSON.write_text(
        json.dumps(schema_obj.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] step2 schema saved: {OUT_SCHEMA_JSON}")

    print(json.dumps(schema_obj.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()