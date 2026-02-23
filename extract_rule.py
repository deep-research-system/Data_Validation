from __future__ import annotations

import re
import json

from dotenv import load_dotenv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from openai import OpenAI
from openpyxl import Workbook

load_dotenv()


MD_PATH = Path("output/클라우드컴퓨팅_하.md")
OUT_JSON = Path("output/rules.json")
OUT_XLSX = Path("output/rules.xlsx")
MODEL = "gpt-4o-mini"   

# -------------------------
# 0) 파서
# -------------------------
QUESTION_START_RE = re.compile(
    r"""^\s*(?:[-*]\s*)?(?:\#{2,6}\s*)?
        (?P<qid>(?:SQ|DQ)?\d+(?:-\d+)?|[A-Za-z]+\d+(?:-\d+)?)
        \.\s*
    """,
    re.VERBOSE
)

CIRCLED_NUM = {
    "①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5",
    "⑥": "6", "⑦": "7", "⑧": "8", "⑨": "9", "⑩": "10",
    "⑪": "11", "⑫": "12", "⑬": "13", "⑭": "14", "⑮": "15",
    "⑯": "16", "⑰": "17", "⑱": "18", "⑲": "19", "⑳": "20",
}

LOGIC_KEYWORDS = (
    "⇒", "→", "이동", "건너", "스킵", "종료", "응답하지", "선택 불가",
    "중복", "같은", "일치", "이상", "이하", ">=", "<=", ">", "<", "=",
)

QHEADER_RE = re.compile(r"^\s*###\s+([A-Za-z0-9][A-Za-z0-9_\-]*)\s*\.?\s*(.*)$")
CHOICE_RE = re.compile(r"^\s*[-*]\s*(?:(?P<label>[①-⑳])|(?P<num>\d+)[\).]?)\s*(?P<text>.*)$")


@dataclass
class LogicLine:
    qid: str
    text: str
    prev_choice_code: Optional[str] = None  # 있으면 "2" 같은 값


def is_logic_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # blockquote 형태(> ...)는 우선 로직 후보로 간주
    if s.startswith(">"):
        return True
    # 키워드 기반
    return any(k in s for k in LOGIC_KEYWORDS)


def extract_choice_code(line: str) -> Optional[str]:
    m = CHOICE_RE.match(line)
    if not m:
        return None
    label = m.group("label")
    if label and label in CIRCLED_NUM:
        return CIRCLED_NUM[label]
    num = m.group("num")
    if num:
        return num
    return None


def parse_md_to_logic_lines(md_text: str) -> List[LogicLine]:
    lines = md_text.splitlines()

    current_qid: Optional[str] = None
    out: List[LogicLine] = []

    prev_nonempty = ""

    for line in lines:
        m = QUESTION_START_RE.match(line)
        if m:
            current_qid = m.group("qid").strip()
            prev_nonempty = ""
            continue

        if current_qid is None:
            continue

        if is_logic_line(line):
            prev_choice = extract_choice_code(prev_nonempty)
            out.append(
                LogicLine(
                    qid=current_qid,
                    text=line.strip(),
                    prev_choice_code=prev_choice
                )
            )

        if line.strip():
            prev_nonempty = line

    return out

# -------------------------
# 1) LLM 구조화 (Rule = if/then)
# -------------------------

RULES_JSON_SCHEMA: Dict[str, Any] = {
    "name": "survey_rules",
    "schema": {
        "type": "object",
        "properties": {
            "rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "qid": {"type": "string"},
                        "if": {"type": "string"},
                        "then": {"type": "string"},
                        "raw": {"type": "string"},
                    },
                    "required": ["qid", "if", "then", "raw"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["rules"],
        "additionalProperties": False,
    }
}


def build_llm_input(logic_lines: List[LogicLine], max_lines: int = 120) -> str:
    # 너무 길어지면 컷 (일단 단순하게)
    items = logic_lines[:max_lines]
    rows = []
    for i, ll in enumerate(items, 1):
        # prev_choice_code는 “힌트”일 뿐. 없으면 빈칸.
        hint = f"prev_choice={ll.prev_choice_code}" if ll.prev_choice_code else "prev_choice="
        rows.append(f"{i}. qid={ll.qid} | {hint} | text={ll.text}")
    return "\n".join(rows)


def call_llm_structuring(client: OpenAI, model: str, logic_lines: List[LogicLine]) -> List[Dict[str, Any]]:
    """
    Structured Outputs (json_schema)로 'rules' 배열을 강제한다.
    """
    instructions = """
너는 설문 규칙 구조화 엔진이다.

출력 규칙(중요):
- 반드시 JSON만 출력한다.
- 최상위는 { "rules": [...] } 형식이다.
- rules의 각 원소는 {qid, if, then, raw, note?} 이다.
- qid는 입력 qid 그대로 사용한다.

IF(조건) 문법:
- 단일 선택: Q8=2
- 여러 값: Q8 in {4,5}
- 미응답: Q8 is missing
- 응답함: Q8 is answered
- 비교: A1 >= A2

THEN(행동) 문법:
- 이동: GOTO A
- 종료: END
- 금지: FORBID (Q1=1 & Q2=1)
- 필수: REQUIRE Q7 answered
- 존재: REQUIRE EXISTS(Q1..Q5 value=1)

판단:
- text에 '⇒', '이동', '다음 문항'이 있으면 보통 GOTO
- '종료'가 있으면 END
- '선택 불가/중복/같은 번호'면 FORBID
- '일치/비교/이상/이하'면 비교 규칙으로 if/then을 최대한 단순화

힌트:
- prev_choice가 있으면 보통 조건에 qid=prev_choice를 사용한다.
- 애매하면 note에 짧게 이유를 남기고, if/then은 최대한 보수적으로 작성한다.
"""

    user_input = build_llm_input(logic_lines)

    # response_format json_schema 형태는 공식 문서 예시를 따른다. :contentReference[oaicite:1]{index=1}
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_input},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": RULES_JSON_SCHEMA["name"],
                "schema": RULES_JSON_SCHEMA["schema"],
                "strict": True,
            },
        },
    )

    content = resp.choices[0].message.content
    data = json.loads(content)
    return data["rules"]


# -------------------------
# 2) Export: JSON + XLSX
# -------------------------

def save_json(rules: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def save_xlsx(rules: List[Dict[str, Any]], out_path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "rules"
    ws.append(["qid", "if", "then", "raw", "note"])

    for r in rules:
        ws.append([
            r.get("qid", ""),
            r.get("if", ""),
            r.get("then", ""),
            r.get("raw", ""),
            r.get("note", ""),
        ])

    wb.save(out_path)


def main():
    print("MD 읽는중...")
    md_text = MD_PATH.read_text(encoding="utf-8")

    print("로직 라인 추출중...")
    logic_lines = parse_md_to_logic_lines(md_text)

    print(f"로직 후보 수: {len(logic_lines)}")
    print("=== MD 상위 60줄 ===")
    print("\n".join(md_text.splitlines()[:60]))
    print("====================")

    print("=== 로직 후보 30개 미리보기 ===")
    for ll in logic_lines[:30]:
        print(ll.qid, ll.prev_choice_code, ll.text)
    print("===============================")
    client = OpenAI()

    print("LLM 구조화중...")
    rules = call_llm_structuring(client, MODEL, logic_lines)
    print(f"추출된 규칙 수: {len(rules)}")

    save_json(rules, OUT_JSON)
    save_xlsx(rules, OUT_XLSX)

    print("완료.")

if __name__ == "__main__":
    main()