# llm_md_to_survey_json.py
# pip install openai
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

from openai import OpenAI

client = OpenAI(api_key=os.environ[""])

# --- 1) 최소 청킹: MD를 문항 블록으로 분리 ---
# "## ... A4. ..." / "A4. ..." / " - A4. ..." 같은 패턴을 새 문항 시작으로 취급
Q_START_RE = re.compile(r"^\s*(?:##\s*)?.*?\b([A-Za-z]\d+(?:-\d+)?)\.\s+")

def split_into_question_blocks(md_text: str) -> List[str]:
    lines = md_text.splitlines()
    blocks: List[str] = []
    buf: List[str] = []

    def flush():
        nonlocal buf
        if buf:
            block = "\n".join(buf).strip()
            if re.search(r"\b[A-Za-z]\d+(?:-\d+)?\.\s+", block):
                blocks.append(block)
            buf = []

    for ln in lines:
        if Q_START_RE.search(ln):
            flush()
        buf.append(ln)

    flush()
    return blocks


# --- 2) LLM 프롬프트 ---
SYSTEM_PROMPT = """너는 설문지 마크다운을 구조화된 JSON으로 변환하는 파서다.
반드시 JSON만 출력하고, 그 외 텍스트(설명/주석/코드펜스)를 절대 출력하지 마라."""

def build_user_prompt(block: str) -> str:
    return f"""
다음은 설문지 문항 1개 블록의 마크다운이다. 이를 아래 스키마의 JSON 하나로 변환하라.

[출력 JSON 스키마]
{{
  "id": "A4 같은 문항 ID",
  "text": "문항 질문 텍스트(보기/부가문구 제외)",
  "type": "single_choice | multi_choice | text | numeric 중 하나",
  "options": [
    {{"code":"1","label":"전혀 아니다","goto":"A4-1 또는 null"}}
  ],
  "notes": ["문항 부가설명/조건/※표기 등(선택)"]
}}

[규칙]
- 선택지 코드: ①→"1", ②→"2" 처럼 숫자 문자열로 통일
- goto 추출:
  - 선택지 라인에 (⇒ A4-1 이동) 등이 붙어있으면 해당 선택지 goto에 넣어라.
  - 별도 라인에 "(⇒ A4-1 이동) (⇒ A5 이동) ..." 처럼 여러 개가 한 줄에 나열되면,
    options 순서대로 goto를 1:1 매핑하라.
- "A5. ..." 같은 다음 문항 텍스트가 options.label로 섞이면 안 된다.
- 출력은 JSON 1개 객체만.

[입력 블록]
<<<
{block}
>>>
""".strip()


# --- 3) LLM 호출 (구현만, 실패/검증/재시도 없음) ---
def llm_parse_question_block(block: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(block)},
        ],
        temperature=0,
    )
    text = resp.choices[0].message.content.strip()
    return json.loads(text)


# --- 4) 전체 실행: MD -> blocks -> LLM -> 합치기 ---
def md_to_survey_json(md_path: str | Path, out_json_path: str | Path, model: str = "gpt-4.1-mini") -> Path:
    md_path = Path(md_path)
    out_json_path = Path(out_json_path)

    md_text = md_path.read_text(encoding="utf-8")
    blocks = split_into_question_blocks(md_text)

    questions = []
    for b in blocks:
        q = llm_parse_question_block(b, model=model)
        questions.append(q)

    survey = {
        "title": md_path.stem,
        "questions": questions,
    }

    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(survey, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_json_path


if __name__ == "__main__":
    # 예시: data/pdf_markdown/pdf_test2.md -> data/pdf_markdown/pdf_test2.llm.json
    in_md = Path("data/pdf_markdown/pdf_test2.md")
    out_json = in_md.with_suffix(".llm.json")
    saved = md_to_survey_json(in_md, out_json, model="gpt-4.1-mini")
    print("saved:", saved)
