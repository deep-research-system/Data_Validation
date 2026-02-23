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
text = Path("output/요양시설_중상.md").read_text(encoding="utf-8")

# ----- (2) 파서 준비 -----
parser = PydanticOutputParser(pydantic_object=ValidationSchema)
format_instructions = parser.get_format_instructions()

# ----- (3) 프롬프트: 스킵만 + JSON만 출력 강제 -----
system_prompt = f"""
너는 설문지 Markdown/TXT에서 '조건부 이동 로직(스킵)'만 추출하는 엔진이다.

[핵심 임무]
- 보기 선택(①/②/③ 등) 또는 조건문 때문에
  문항이 다른 문항으로 이동하거나,
  특정 문항군만 응답하도록 지시하는 문장만 추출한다.
- 이동과 무관한 설명/안내/일반 질문 텍스트는 절대 포함하지 않는다.

────────────────────────
[중요한 원칙 — 생성 금지 규칙]
────────────────────────
아래 조건을 충족하지 않으면 절대 스킵 규칙을 만들지 마라.

1) raw 문장 안에 다음 중 하나가 반드시 명시적으로 포함되어야 한다:
   - "☞"
   - "⇒" 또는 "→"
   - "이동"
   - "건너뛰"
   - "설문 종료"
   - "~로 가시오"
   - "~로 진행"

2) 위 단어/기호가 없는 경우:
   - 단순 보기(①②③ 등)만 있는 문항은 스킵이 아니다.
   - 다음 문항으로 자연스럽게 이어지는 것은 스킵이 아니다.
   - LLM이 추론해서 end_col을 만들어서는 안 된다.

3) 다음 문구는 스킵 근거가 아니다 (절대 규칙 생성 금지):
   - "모두 표시"
   - "복수응답"
   - "해당하는 것을 표시"
   - "해당항목 모두 표시"
   - "응답 3가지"
   - 체크/안내 문구

4) end_col은 raw에 명시된 경우에만 작성한다.
   - "다음 문항"을 추론하지 마라.
   - "자연스럽게 이어지는 문항"을 상식으로 생성하지 마라.

위 표식/단어가 없는 문항은, 보기(①②③)가 있어도 절대 스킵 로직으로 추출하지 마라.
(예: 문15, 문17처럼 그냥 보기만 있는 문항은 제외)

[분류 규칙]

1) SkipRule (type="skip")
- 조건 충족 시 즉시 특정 문항으로 점프하는 경우
- 예: "☞ 문4로 이동", "→ A7로 이동"


[value 규칙]
- 보기번호는 문자열 리스트 형태로 통일: ["1"], ["2"], ["3"]
- ①②③ → 각각 "1","2","3"으로 변환
- ②/③ 또는 ②,③ → ["2","3"]

[문항 ID 규칙]
- start_col / mid_col / end_col은 설문에 표시된 문항 ID를 그대로 사용
  예: "문3-1", "3-2-1", "문14-4", "Q8", "A37"
- '문' 접두어는 임의로 제거하거나 추가하지 말 것

[raw 규칙]
- raw에는 설문지의 원문 지시문을 가능한 한 그대로 복사한다.
- 의미를 바꾸지 말 것.

[그룹 규칙]
- 동일한 start_col에 대한 규칙은 하나의 RuleGroup으로 묶는다.
- start_col이 다르면 그룹을 분리한다.

[출력 제약]
- 반드시 JSON 객체 하나만 출력한다.
- 설명, 주석, 코드블록, 마크다운, 텍스트 추가 금지.
- 스키마에 없는 키를 추가하지 말 것.
- 이동 로직이 없는 문항은 출력하지 말 것.

출력형태
------------------------
{format_instructions}
------------------------
"""

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=text)
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

Path("output/요양시설_중상.json").write_text(
    json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False),
    encoding="utf-8"
)
