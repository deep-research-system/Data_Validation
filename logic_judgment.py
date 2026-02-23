from dotenv import load_dotenv
from pathlib import Path
from schema import ValidationSchema
import json

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException

load_dotenv()

# gpt 모델 초기화
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)



# PDF에서 추출한 텍스트 불러오기
text = Path("output/한국생산기술연구원_중.txt").read_text(encoding="utf-8")

# ----- (2) 파서 준비 -----
parser = PydanticOutputParser(pydantic_object=ValidationSchema)
format_instructions = parser.get_format_instructions()

# ----- (3) 프롬프트: 스킵만 + JSON만 출력 강제 -----
system_prompt = f"""
너는 통계 조사 설문지를 분석하는 전문가다.

너의 임무는 입력된 설문지 텍스트에서 "조건부 이동 로직"을 찾아,
아래 JSON 스키마(ValidationSchema)에 맞춰 구조화하여 출력하는 것이다.
출력은 오직 JSON만 허용한다.

━━━━━━━━━━━━━━━━━━━━
[1. 로직 유형 정의: skip vs branch_skip]
━━━━━━━━━━━━━━━━━━━━

※ 두 유형은 "문장 패턴"으로만 판정한다. 추론 금지.

(1) skip 규칙 (단순 이동)
- 원문 패턴: "(X로 이동)" / "(⇒ X로 이동)" / "X로 이동" / "설문 종료" / "이후 문항 응답하지 않음"
- 특징: "응답 후", "~만 응답" 문구가 없다.
- 처리:
  - end_col = 이동 대상 X
  - start_col = 해당 지시문이 속한 문항ID
  - value = 해당 지시문이 대응하는 선택지 번호(①=1, ②=2, ...)
- 금지:
  - "X로 이동"에서 X를 mid_col로 쓰면 안 된다. X는 end_col이다.
  - end_col을 원문에 없는 문항으로 추론해서 만들면 안 된다.

(2) branch_skip 규칙 (경유 응답 후 이동)
- 원문 패턴: 반드시 아래 표현이 포함되어야 한다.
  - "응답 후"
  - "~만 응답 후"
  - "~만 응답하고"
- 특징: "중간에 응답해야 할 문항(mid_col)"이 명시되고, 그 후 최종 이동(end_col)이 명시된다.
- 처리:
  - mid_col = "응답 후" 또는 "~만 응답"으로 명시된 문항ID(들)만 기록
  - end_col = "…으로 이동"에서 이동 대상 문항ID만 기록
  - start_col/value는 skip과 동일 규칙으로 기록
- 금지(매우 중요):
  - "(C2-1로 이동)" 같이 '이동'만 있는 문장은 branch_skip이 될 수 없다. 이런 경우는 무조건 skip이다.
  - mid_col과 end_col은 반드시 원문에 명시된 문항ID만 사용한다. 추론/추가 생성 금지.
  - "응답 후"가 없으면 branch_skip 금지.

━━━━━━━━━━━━━━━━━━━━
[2. 추출 단위 및 매칭 규칙]
━━━━━━━━━━━━━━━━━━━━

- 로직 지시문(☞, ⇒, 괄호 지시 등)은 반드시 특정 문항(start_col)의 선택지(value)에 매칭되어야 한다.
- 예: "① ... ☞ (B1-1, B1-2 응답 후 C1으로 이동)" 이면 value=[1]
- B1처럼 ①② 지시문과 ③④ 지시문이 줄이 바뀌어 나타날 수 있다.
  → 따라서 start_col 문항의 모든 선택지(예: ①~④)를 끝까지 훑고 누락 없이 추출한다.
- end_col은 반드시 "…로 이동"에서 등장한 문항ID를 그대로 복사한다.
- branch_skip에서 mid_col은 "응답 후" 또는 "~만 응답"으로 명시된 문항ID만 적는다.
  (이동 대상은 mid_col이 아니라 end_col이다.)

━━━━━━━━━━━━━━━━━━━━
[3. 출력 스키마]
━━━━━━━━━━━━━━━━━━━━
{format_instructions}

━━━━━━━━━━━━━━━━━━━━
[4. 검증 규칙]
━━━━━━━━━━━━━━━━━━━━

- 스키마 키/자료형이 하나라도 어긋나면 그 로직은 출력하지 않는다.
- 조건(value) 또는 start_col 또는 end_col이 원문에서 명확하지 않으면 제외한다.
- branch_skip은 반드시 "응답 후" 또는 "~만 응답" 문구가 있을 때만 출력한다.
- 출력은 JSON만. 다른 텍스트 금지.
"""

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=f"설문지 원문 텍스트:\n\n{text}")
]


# ----- (4) 호출 + 파싱 -----
raw = llm.invoke(messages).content

try:
    schema_obj = parser.parse(raw)   # ValidationSchema 객체
except OutputParserException as e:
    print("파싱 실패. 원문 응답(raw)을 확인하세요.")
    print(raw)
    raise

print(json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False))

Path("output/한국생산기술연구원_중_schema.json").write_text(
    json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False),
    encoding="utf-8"
)
