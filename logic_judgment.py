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
text = Path("output/pdf_text(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.txt").read_text(encoding="utf-8")

# ----- (2) 파서 준비 -----
parser = PydanticOutputParser(pydantic_object=ValidationSchema)
format_instructions = parser.get_format_instructions()

# ----- (3) 프롬프트: 스킵만 + JSON만 출력 강제 -----
system_prompt = f"""
너는 통계 조사 설문지를 분석하는 전문가다.
목표: 설문지에서 '스킵 로직(조건부 문항 이동/건너뛰기/종료)'만 추출해서,
아래 Pydantic 스키마(JSON)로만 출력한다.

[중요]
- 기본 흐름(그냥 다음 문항)은 로직이 아니다. 절대 포함하지 마라.
- 이동 대상은 반드시 실제 문항 ID여야 한다. (예: B2, C3-1, D10)
- 원문에 없는 로직은 추론하지 마라.
- 출력은 반드시 "JSON 한 덩어리"만. 설명/해설/마크다운 금지.

[값 규칙]
- start_col: 조건이 걸리는 문항 ID (예: B2, C3-1, D10)
- value: 그 조건 값(선택지 코드/문자열). 원문에 보이는 그대로.
- end_col: 이동할 문항 ID (설문 종료라면 end_col을 "END"로 쓰지 말고, 가능하면 실제 문항/종료 표기를 문항 ID 규칙에 맞춰 추출. 문항ID가 없으면 스킵으로 추출하지 마라.)
- items: 이 rule을 공유하는 문항 리스트. 보통 [start_col]로 두면 된다.

[출력 스키마]
{format_instructions}
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

Path("schema.json").write_text(
    json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False),
    encoding="utf-8"
)

# messages = [
#     SystemMessage(
#         content=("""
#                  너는 통계 조사 설문지를 분석하는 전문가다.
#                  너의 임무는 설문지에 포함된 "설문지 로직"을 식별하는 것이다.

#                 [기본 흐름과 로직의 구분 - 매우 중요]
#                 - 설문지는 기본적으로 문항 순서대로 다음 문항으로 진행된다.
#                 - 이 기본적인 "다음 문항으로 이동"은 설문지 로직이 아니다.
#                 - 따라서 아래에 해당하는 경우는 로직으로 간주하지 마라.
#                 - "다음 문항으로 이동"
#                 - 이동 대상이 명시되지 않은 경우
#                 - "기타(▶ )"처럼 선택지는 있으나 이동 문항 ID가 지정되지 않은 경우
#                 - 기본 흐름상 자연스럽게 다음 문항으로 이어지는 경우

#                 [설문지 로직 정의]
#                 설문지 로직이란, 응답자의 선택에 따라
#                 - 특정 문항을 건너뛰거나
#                 - 특정 문항으로 이동하거나
#                 - 이후 문항을 응답하지 않도록 지시하는
#                 조건부 분기(스킵) 문장을 의미한다.

#                 [로직 식별 기준]
#                 다음과 같은 의미를 포함한 문장만 설문지 로직으로 간주한다.
#                 - "문항 이동/건너뛰기" 로직만 추출한다. (예: "B2로 이동", "B1-1로 이동", "다음 문항으로 이동", "설문 종료")
#                 "추가 기입/이유 작성/서술 요구"는 로직으로 보지 말고 제외한다.(예: "불편함을 느낌 이유:", "구체적으로:", "기타( )", "서술하시오" 등)
                
#                 [이동 로직 판별의 필수 조건]
#                 - 이동 대상은 반드시 실제 "문항 ID"여야 한다.
#                 - 문항 ID란 다음 형식을 만족해야 한다:
#                 - 영문 대문자 1자 이상 + 숫자 (예: B2, C5, D10)
#                 - 또는 하위 문항 형태 (예: B1-1, C3-2)
#                 - 위 형식을 만족하지 않는 대상은 이동 로직으로 간주하지 마라.

#                 [명시적 제외 규칙 - 매우 중요]
#                 다음은 어떤 경우에도 설문지 로직으로 추출하지 마라.
#                 - 이동 대상이 문항 ID가 아닌 경우
#                 (예: "이유:", "구체적으로:", "기타", "내용", 공란)
#                 - "추가 기입", "서술", "이유 작성"을 요구하는 표현
#                 - "기타( )"처럼 이동 대상이 비어 있거나 불명확한 경우
#                 - 기본 진행(next question)에 해당하는 문장은 어떤 경우에도 출력하지 마라.

#                 [중요 제한 사항]
#                 - 일반 문항 설명, 안내 문구, 조사 목적 설명은 포함하지 마라.
#                 - 응답 선택지 설명 자체는 로직이 아니다.
#                 - 원문에 명시되지 않은 로직을 추론하거나 생성하지 마라.

#                 [출력 규칙]
#                 - 설문지 로직에 해당하는 문장을 추출한다.
#                 - 반드시 문항 ID(Q번호) 기준으로 정리한다.
#                 - 로직이 전혀 없을 경우, "설문지 로직 없음"이라고만 출력한다.
#                 - 각 추출 항목마다 왜 로직으로 판단했는지 1줄 근거를 원문 그대로 인용해라
#                 """
#         )
#     ),
#     HumanMessage(
#         content=f"""
# 아래는 설문지 원문 텍스트다.


# 텍스트:
# {text}
# """
#     ),
# ]



# response = llm.invoke(messages)

# print("TEXT_LEN:", len(text))
# # print("TEXT_HEAD:", text[:300])

# print(response.content)