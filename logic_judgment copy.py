from dotenv import load_dotenv
from pathlib import Path
import json
import re
from typing import List, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# ----------------------------
# LLM 초기화 (애매 케이스용)
# ----------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ----------------------------
# 정규식 정의
# ----------------------------
CHOICE_RE = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]")
MOVE_RE = re.compile(r"⇒\s*([A-Z][A-Z0-9\-\.ⓐⓑ]*)")

CIRCLED_NUM_MAP = {
    "①":"1","②":"2","③":"3","④":"4","⑤":"5",
    "⑥":"6","⑦":"7","⑧":"8","⑨":"9","⑩":"10"
}

# ----------------------------
# 유틸 함수
# ----------------------------
def normalize_id(x: str) -> str:
    """마침표 및 불필요 텍스트 제거"""
    x = x.rstrip(".")
    x = re.sub(r"\s*로 이동.*", "", x)
    return x.strip()

def extract_choices(raw: str) -> List[str]:
    found = CHOICE_RE.findall(raw)
    return [CIRCLED_NUM_MAP[c] for c in found]

def extract_moves(raw: str) -> List[str]:
    found = MOVE_RE.findall(raw)
    return [normalize_id(x) for x in found]

# ----------------------------
# Python 자동 매칭 로직
# ----------------------------
def auto_match(start: str, raw: str) -> Optional[List[Dict]]:
    start = start.rstrip(".")
    choices = extract_choices(raw)
    moves = extract_moves(raw)

    if not choices or not moves:
        return []

    rules = []

    # 1:1 매칭
    if len(choices) == len(moves):
        for v, end in zip(choices, moves):
            rules.append({
                "type": "skip",
                "start": start,
                "value": v,
                "end": end,
                "raw": raw,
                "note": ""
            })
        return rules

    # 이동 1개 + 보기 여러개
    if len(moves) == 1:
        for v in choices:
            rules.append({
                "type": "skip",
                "start": start,
                "value": v,
                "end": moves[0],
                "raw": raw,
                "note": ""
            })
        return rules

    # 애매 케이스 → LLM으로 넘김
    return None

# ----------------------------
# LLM 보조 함수 (1개 후보용)
# ----------------------------
def call_llm_for_one_candidate(cand: Dict) -> List[Dict]:
    prompt = f"""
다음 raw에서 스킵 로직을 정확히 분해하라.
value는 단일값.
start는 {cand["start_hint"].rstrip(".")}
raw:
{cand["raw"]}

JSON 배열만 출력.
"""

    messages = [
        SystemMessage(content="너는 스킵 로직 분해기다."),
        HumanMessage(content=prompt)
    ]

    raw = llm.invoke(messages).content

    try:
        parsed = json.loads(raw)
        return parsed
    except:
        return []

# ----------------------------
# 후보 JSON 로드
# ----------------------------
candidate_path = Path("output/부산연구원_상_c.json")
candidate_data = json.loads(candidate_path.read_text(encoding="utf-8"))

print("후보 개수:", len(candidate_data.get("items", [])))

# ----------------------------
# 최종 처리
# ----------------------------
final_rules = []

for cand in candidate_data["items"]:
    result = auto_match(cand["start_hint"], cand["raw"])

    if result is None:
        # 복잡 케이스만 LLM
        llm_rules = call_llm_for_one_candidate(cand)
        final_rules.extend(llm_rules)
    else:
        final_rules.extend(result)

# 중복 제거
seen = set()
cleaned = []

for r in final_rules:
    key = (r["start"], r["value"], r["end"])
    if key in seen:
        continue
    seen.add(key)
    cleaned.append(r)

output = {"rules": cleaned}

# ----------------------------
# 저장
# ----------------------------
out_path = Path("output/부산연구원_상.json")
out_path.write_text(
    json.dumps(output, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("최종 rule 개수:", len(cleaned))
print("완료:", out_path)