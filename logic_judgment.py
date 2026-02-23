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
text = Path("output/계약의사_하.md").read_text(encoding="utf-8")

# ----- (2) 파서 준비 -----
parser = PydanticOutputParser(pydantic_object=ValidationSchema)
format_instructions = parser.get_format_instructions()

# ----- (3) 프롬프트: 스킵만 + JSON만 출력 강제 -----
system_prompt = f"""
너는 설문지 Markdown/TXT에서 '조건부 이동 로직(스킵)'을
빠짐없이 추출하는 엔진이다.

────────────────────────
[최우선 목표]
────────────────────────
1) 설문지에 실제로 존재하는 스킵 로직은 단 하나도 누락하지 않는다.
2) 설문지에 존재하지 않는 이동을 절대 추론해서 만들어내지 않는다.
3) 설문지에 존재하는 문항 ID를 전부 정확히 추출한다.

────────────────────────
[스킵 로직 정의]
────────────────────────
다음과 같이 보기 선택 또는 조건에 따라
특정 문항으로 이동하도록 명시적으로 지시하는 문장만 스킵 로직이다.

다음 표현이 포함되면 반드시 스킵으로 추출한다:

- "☞"
- "⇒"
- "→"
- "이동"
- "건너뛰"
- "~로 가시오"
- "~로 진행"
- "~응답한 경우 문X"
- "~응답자는 문X"

예:
- "① 예 ☞ 문4로 이동"
- "② 아니오 → 문8"
- "① 있음 ☞ 3-1-1로 이동"
- "② 없음 ☞ 문4"

위와 같이 '문항 이동 지시'가 명시되어 있으면 반드시 포함한다.

[skip] 블록이 여러 개면, 각각을 가장 논리적으로 일치하는 보기(하위문항 언급 기준)로 매핑하라

────────────────────────
[중요 — 추론 금지 규칙]
────────────────────────
다음은 절대 스킵으로 만들지 마라:

- 보기(①②③ 등)만 있고 이동 지시가 없는 경우
- "모두 표시", "복수응답", "해당하는 것 표시" 등 체크 안내

⚠ raw에 이동 지시가 명시되지 않으면 규칙을 생성하지 마라.


────────────────────────
[value 규칙]
────────────────────────
- 보기 번호는 문자열 리스트 형태로 통일한다.
- ①②③ → 각각 "1","2","3"
- ②/③ → ["2","3"]

[value 묶기(압축) 규칙]

1) value를 여러 개로 묶는 것은 "동일한 이동 지시 문장(raw)"이
   '보기 라인'에서 반복되는 경우에만 허용한다.
   예: "④ ... ☞ 문17-1", "⑤ ... ☞ 문17-1"

2) [skip] 블록(주석형 스킵)에서는 value를 절대 여러 개로 묶지 마라.
   [skip]은 항상 바로 위 보기 1개에만 귀속한다.

3) 즉, value 묶기는 "보기 라인에 붙은 이동(☞/→/⇒)" 에서만 허용,
   "설명/주석/괄호형 스킵([skip])" 에서는 금지.
   
────────────────────────
[문항 ID 규칙]
────────────────────────
- start_col과 end_col은 설문지에 적힌 문항 ID를 그대로 사용한다.
- "문" 접두어를 임의로 제거하거나 추가하지 않는다.
- "☞ 문4-2"처럼 '로 이동'이 생략된 경우도 이동으로 인정한다.

────────────────────────
[그룹 규칙]
────────────────────────
- 동일한 start_col은 하나의 그룹으로 묶는다.
- 서로 다른 문항은 그룹을 분리한다.
- 실제 분기되는 문항 단위로 그룹을 구성한다.

────────────────────────
[출력 제약]
────────────────────────
- 반드시 JSON 객체 하나만 출력한다.
- 설명, 주석, 코드블록, 마크다운 금지.
- 스키마 외 키 추가 금지.
- 스킵이 없는 문항은 출력하지 않는다.

출력형태
--------------------------------
{format_instructions}
--------------------------------
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

Path("output/계약의사_하.json").write_text(
    json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False),
    encoding="utf-8"
)
