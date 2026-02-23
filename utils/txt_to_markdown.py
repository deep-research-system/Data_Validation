# txt_to_md_minimal.py

from pathlib import Path
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


load_dotenv()

# === 1. OpenAI Key 직접 입력 ===

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# === 2. 프롬프트 ===
SYSTEM_PROMPT = """너는 설문지 TXT를 Markdown으로 변환하는 변환기다.

- 구조만 정리한다 (페이지, 문항, 보기, 스킵 로직)
- 의미는 절대 바꾸지 않는다.
- 표로 억지 변환하지 않는다.
- 출력은 Markdown만 한다.

규칙:
1) ===== PAGE N ===== → ## PAGE N
2) Q1, Q2-1 등 문항은 ### 헤더로
3) ①②③ 또는 (1)(2) 등은 리스트로
4) ⇒, 이동, 건너뛰 등은
   > [skip] 원문
형태로 출력
"""

# === 3. TXT 읽기 ===
text = Path("output/계약의사_하.txt").read_text(encoding="utf-8")

# === 4. LLM 호출 ===
response = llm.invoke([
    ("system", SYSTEM_PROMPT),
    ("human", text),
])

markdown = response.content

# === 5. Markdown 파일 생성 ===
Path("output/계약의사_하.md").write_text(markdown, encoding="utf-8")

print("완료: md 생성됨")