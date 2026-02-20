
from __future__ import annotations

import json
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException

from schema import ValidationSchema

# ✅ 후보 블록 생성기(내가 준 코드 파일명 가정)
from utils.candidate import (
    extract_skip_candidates,
    group_candidates_by_qid,
    build_question_blocks,
    build_llm_input_from_blocks,
)

load_dotenv()

# ----------------------------
# 0) 모델
# ----------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ----------------------------
# 1) 원문 로드
# ----------------------------
text_path = Path("output/요양시설_중상.txt")
text = text_path.read_text(encoding="utf-8", errors="replace")

# ----------------------------
# 2) Pydantic 파서 준비
# ----------------------------
parser = PydanticOutputParser(pydantic_object=ValidationSchema)
format_instructions = parser.get_format_instructions()

# ----------------------------
# 3) 후보 블록 생성 (원문 전체 → 후보만)
# ----------------------------
cands = extract_skip_candidates(text, context_lines=2, lookback_qid=40)
grouped = group_candidates_by_qid(cands)
blocks = build_question_blocks(grouped, include_line_numbers=True, max_lines_per_block=120)
skip_blocks_text = build_llm_input_from_blocks(blocks, doc_title="요양시설_중상 스킵 후보 블록")

# 후보 블록 저장(디버그/검토용)
Path("output/요양시설_중상_skip_blocks.txt").write_text(skip_blocks_text, encoding="utf-8")

# ----------------------------
# 4) 프롬프트 (후보 블록 입력 전용)
# ----------------------------
system_prompt = f"""
너는 통계 조사 설문지를 분석하는 전문가다.

입력은 '스킵 로직 후보 블록'이다.
중요: 후보 블록에 포함된 모든 라인이 스킵 로직인 것은 아니다.
너는 후보 블록에서 실제 '조건부 문항 이동(☞/⇒/로 이동/건너뛰기)'만 골라
아래 Pydantic 스키마(JSON)로만 출력한다.

━━━━━━━━━━━━━━━━━━━━
[출력 절대 규칙]
━━━━━━━━━━━━━━━━━━━━
- 출력은 반드시 JSON 한 덩어리만 반환한다. (설명/해설/마크다운/코드블록 금지)
- {format_instructions} 를 반드시 준수한다.
- 스키마에 없는 필드는 절대 추가하지 마라.
- 원문에 없는 문항 ID를 절대 생성하지 마라.
- 원문에 없는 이동 로직을 절대 추론하지 마라.
- 최상위 type 필드는 반드시 "스킵"으로 출력한다.

━━━━━━━━━━━━━━━━━━━━
[문항 ID 규칙]
━━━━━━━━━━━━━━━━━━━━
- 문항 ID는 입력 블록에 등장한 형태를 그대로 사용한다.
- "4-2"와 "문4-2"를 혼용하지 마라.
  - 입력이 "4-2"면 "4-2"로.
  - 입력이 "문4-2"면 "문4-2"로.

━━━━━━━━━━━━━━━━━━━━
[스킵 로직 판정 - 오탐 제거 핵심]
━━━━━━━━━━━━━━━━━━━━
스킵 로직으로 추출하는 경우는 오직 "선택지에 이동 지시 + 이동 대상 문항ID"가 명시된 경우뿐이다.

다음은 절대 스킵 로직이 아니다(후보 블록에 있어도 제외):
1) 추가 기입/보충 정보/보기 확장(하위 항목 나열)
   - 예: "☞ 요양시설 최초 설치년도"
   - 예: "☞ 전문분야(중복응답)"
   - 예: "☞ 전문간호사 자격 : ① 있음 ② 없음"
2) "모두 표시", "해당사항 표시", "기입" 등
   - 예: "☞ 병설 기관 유형 모두 표시"
   - 예: "☞ 야간근무 간호인력 모두 표시"

※ 이동으로 인정되는 형태:
- "① ... ☞ 3-2-1로 이동"
- "② ... ☞ 문5로 이동"
- "① ... ☞ 문4-3~문4-6로 이동" (범위는 이동으로 인정)

━━━━━━━━━━━━━━━━━━━━
[필드별 강제 규칙 - items 오류/누락 방지]
━━━━━━━━━━━━━━━━━━━━
- items: 항상 [start_col] 로만 출력한다. (문장/보기 금지)

- value: 선택지 코드+선택지 텍스트만.
  - 이동 지시/이동 대상/로 이동 문구는 value에 포함 금지.
  - 예: "① 있음 ☞ ( ) 명 ☞ 3-1-1로 이동" → value는 "① 있음"
  - 예: "② 없음 ☞ 문4로 이동" → value는 "② 없음"

- end_col: 이동할 문항ID만.
  - 범위 이동이면 end_col은 범위 시작 문항만.
    예: "문4-3~문4-6로 이동" → end_col="문4-3"
  - end_col에는 "~" 문자를 포함하지 마라.

- note: 반드시 2줄
  1줄: 근거(☞/⇒/로 이동) + 이동 대상 요약(범위면 범위 포함)
  2줄: "items:<start_col> | type:skip | value:<value[0]> | end_col:<end_col>"

━━━━━━━━━━━━━━━━━━━━
[분기 완결성 체크(누락 방지)]
━━━━━━━━━━━━━━━━━━━━
- 같은 문항(start_col)에 이동 지시가 여러 개면, 그 개수만큼 반드시 모두 rule로 출력한다.
  예: "① ... ☞ X ② ... ☞ Y"면 2개 모두.
- 특히 "있음/없음", "예/아니오", "알고 있다/모른다" 같은 쌍은 반드시 둘 다 확인한다.

━━━━━━━━━━━━━━━━━━━━
[출력 스키마]
━━━━━━━━━━━━━━━━━━━━
{format_instructions}
"""

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=skip_blocks_text),
]

# ----------------------------
# 5) 호출 + 파싱
# ----------------------------
raw = llm.invoke(messages).content

# raw 저장(파싱 실패 디버깅용)
Path("output/요양시설_중상_raw.json").write_text(raw, encoding="utf-8")

try:
    schema_obj = parser.parse(raw)
except OutputParserException:
    print("파싱 실패. raw를 확인하세요:")
    print(raw)
    raise

# ----------------------------
# 6) 결과 저장
# ----------------------------
out_json = json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False)
print(out_json)

Path("output/요양시설_중상_schema.json").write_text(out_json, encoding="utf-8")
print("저장 완료: output/요양시설_중상_schema.json")