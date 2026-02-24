from dotenv import load_dotenv
from pathlib import Path
from schema import ValidationSchema
import json

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException
from prompts import system_prompt_judgment

load_dotenv()

# gpt 모델 초기화
llm = ChatOpenAI(model="gpt-5-nano")



# PDF에서 추출한 텍스트 불러오기
text = Path("output/부산연구원_상_c.json").read_text(encoding="utf-8")

# ----- (2) 파서 준비 -----
parser = PydanticOutputParser(pydantic_object=ValidationSchema)
format_instructions = parser.get_format_instructions()

# ----- (3) 프롬프트: 스킵만 + JSON만 출력 강제 -----
system_prompt_judgment = system_prompt_judgment.format(format_instructions=format_instructions)

candidate_json = Path("output/부산연구원_상_c.json").read_text(encoding="utf-8")

print("입력 문자열 길이:", len(candidate_json))
print("입력 앞부분 미리보기:")
print(candidate_json[:1000])   # 앞 1000자만 확인

candidate_data = json.loads(candidate_json)
print("후보 개수:", len(candidate_data.get("items", [])))

messages = [
    SystemMessage(content=system_prompt_judgment),
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

Path("output/부산연구원_상.json").write_text(
    json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False),
    encoding="utf-8"
)
