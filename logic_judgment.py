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
text = Path("output/클라우드컴퓨팅_하.txt").read_text(encoding="utf-8")

# ----- (2) 파서 준비 -----
parser = PydanticOutputParser(pydantic_object=ValidationSchema)
format_instructions = parser.get_format_instructions()

# ----- (3) 프롬프트: 스킵만 + JSON만 출력 강제 -----
system_prompt = f"""
너는 "설문지 조건부 이동(스킵) 로직" 추출기다.
입력으로 설문지 원문 텍스트가 주어진다. 너의 목표는 조건부 분기/이동 지시문을 찾아
아래 Pydantic 스키마에 정확히 맞는 JSON만 출력하는 것이다.

[중요 원칙]
1) "조건부 이동/건너뛰기/종료"에 해당하는 문장만 추출한다.
2) 로직처럼 보이더라도 "정확한 문항ID(start_col/end_col)가 둘 다 명시적으로 존재"하지 않으면 절대 스킵 로직으로 기록하지 않는다.
3) 추가 기입/이유 서술/기타( )/설명 요구/응답 대상 안내(예: '취업자만 응답')는 로직이 아니다. 이동/스킵/종료 지시가 없으면 제외한다.
4) 출력은 반드시 아래 스키마 구조의 JSON 1개만. 그 외 텍스트/설명/마크다운 금지.

[문항ID 정의]
- 문항ID는 설문지에서 질문을 식별하는 토큰이다. 예: "Q2-1", "A7", "B5-1", "문3-1", "1-2-4" 등
- 숫자만(예: "3")도 문항ID로 허용한다(원문에 그렇게 표기된 경우).
- 반드시 원문에 나타난 형태 그대로 보존한다(예: A1을 1로 바꾸지 않음).

[스킵 로직 판단 기준]
다음 패턴(및 유사 표현)에서 "조건(선택/응답값)" + "이동(다른 문항ID로)"가 동시에 확인되면 스킵 로직 후보로 본다.
- 기호/표현: "⇒", "->", "→", ">", "이동", "건너뛰기", "로 이동", "응답 후 ~ 이동", "선택 시 ~ 이동", "해당 시 ~ 이동", "인 경우 ~ 이동"
- 예: "② 아니오 (⇒ A7. 응답 후 A39. 이동)"
- 예: "(⇒ B.경제활동으로 이동)" 처럼 목적지가 '파트/섹션' 이름만 있고 문항ID가 없으면 제외한다(문항ID가 명확하지 않기 때문).
- "설문 종료/면접 종료/조사 종료"도 '종료' 문항ID가 명시되지 않으면 제외한다.

[값(value) 추출 규칙]
- value는 start_col(현재 문항)의 응답값 조건이다.
- 원문에 "①/②/③…" 또는 "1)/2)..." 같이 선택지가 명시되면, 해당 선택지 번호를 int로 추출한다.
- 선택지 번호 대신 텍스트 조건만 존재하면(예: "예를 선택한 경우") "예" 같은 문자열로 넣을 수 있다.
- 복수 조건이면 리스트에 모두 포함한다. 예: [1,2] 또는 ["예","아니오"]
- 조건이 명확하지 않으면(이동만 있고 어떤 선택인지 불명) 스킵 로직으로 기록하지 않는다.

[그룹핑 규칙(groups)]
- 동일한 start_col에서 동일한 value 조건으로 동일한 end_col로 이동하는 로직은 하나의 RuleGroup으로 묶는다.
- items에는 해당 로직이 적용되는 문항ID(보통 start_col 1개)를 넣는다. (확장 가능: 동일 규칙이 여러 문항에 반복되면 모두 나열)


[출력 스키마]
━━━━━━━━━━━━━━━━━━━━
{format_instructions}
━━━━━━━━━━━━━━━━━━━━

[검증]
- JSON은 문법적으로 올바르며, 키 이름/자료형이 스키마와 정확히 일치해야 한다.
- 누락 방지를 위해 텍스트 전체를 훑되, 스키마 규칙 위반(문항ID 없음/조건 불명확)이면 과감히 제외한다.


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

Path("output/클라우드컴퓨팅_하_schema.json").write_text(
    json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False),
    encoding="utf-8"
)
