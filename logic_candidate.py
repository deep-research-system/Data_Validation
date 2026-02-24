# from dotenv import load_dotenv
# from pathlib import Path
# from schema import LogicCandidates
# import json

# from langchain_openai import ChatOpenAI
# from langchain_core.output_parsers import PydanticOutputParser
# from langchain_core.messages import SystemMessage, HumanMessage
# from langchain_core.exceptions import OutputParserException
# from prompts import system_prompt_candidate

# import re


# load_dotenv()

# # gpt 모델 초기화
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# # PDF에서 추출한 텍스트 불러오기
# text = Path("output/부산연구원_상.txt").read_text(encoding="utf-8")

# # ----- (2) 파서 준비 -----
# parser = PydanticOutputParser(pydantic_object=LogicCandidates)
# format_instructions = parser.get_format_instructions()

# # ----- (3) 프롬프트: 스킵만 + JSON만 출력 강제 -----
# system_prompt_candidate = system_prompt_candidate.format(format_instructions=format_instructions)

# ### 여기서부터 추가함
# PAGE_SPLIT_RE = re.compile(r"^===== PAGE (\d+) =====\s*$", re.MULTILINE)

# # 문항 헤더(기본형) — 필요시 확장 가능
# Q_HEADER_RE = re.compile(r"^\s*(?:↳\s*)?([A-Z]\d+(?:-\d+)*)(?:\s*[ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙ])?\s*\.", re.UNICODE)

# def split_pages(raw: str):
#     """ (page_no:int, page_text:str) 리스트로 분리 """
#     parts = PAGE_SPLIT_RE.split(raw)
#     # split 결과: [before, pageNo1, pageText1, pageNo2, pageText2, ...]
#     pages = []
#     for i in range(1, len(parts), 2):
#         page_no = int(parts[i])
#         page_text = parts[i+1].strip("\n")
#         pages.append((page_no, page_text))
#     return pages

# def extract_first_json_object(s: str) -> str:
#     """
#     문자열에서 첫 번째 JSON 객체( {...} )만 잘라 반환.
#     - 괄호 균형으로 안전하게 자름
#     """
#     start = s.find("{")
#     if start == -1:
#         raise ValueError("No JSON object start '{' found")

#     depth = 0
#     in_str = False
#     esc = False

#     for i in range(start, len(s)):
#         ch = s[i]
#         if in_str:
#             if esc:
#                 esc = False
#             elif ch == "\\":
#                 esc = True
#             elif ch == '"':
#                 in_str = False
#             continue

#         if ch == '"':
#             in_str = True
#         elif ch == "{":
#             depth += 1
#         elif ch == "}":
#             depth -= 1
#             if depth == 0:
#                 return s[start:i+1]

#     raise ValueError("JSON object not closed properly")

# def add_line_numbers(page_text: str) -> list[str]:
#     lines = [ln.rstrip() for ln in page_text.splitlines()]
#     return [f"[{i+1}] {ln}" for i, ln in enumerate(lines)]

# def chunk_by_question(lines_with_no: list[str]) -> list[str]:
#     """
#     "A11. ~ 다음 A12. 전까지" 처럼 문항 단위로 chunk 만들기.
#     - 헤더가 안 나오면 fallback으로 일정 줄 단위 chunk.
#     """
#     chunks = []
#     cur = []
#     for ln in lines_with_no:
#         # 라인번호 제거한 부분으로 헤더 체크
#         plain = re.sub(r"^\[\d+\]\s*", "", ln)
#         if Q_HEADER_RE.match(plain):
#             if cur:
#                 chunks.append("\n".join(cur).strip())
#                 cur = []
#         cur.append(ln)

#     if cur:
#         chunks.append("\n".join(cur).strip())

#     # 헤더가 거의 없어서 chunk가 1개면 fallback (예: 60줄씩)
#     if len(chunks) <= 1 and len(lines_with_no) > 80:
#         chunks = []
#         step = 60
#         for i in range(0, len(lines_with_no), step):
#             chunks.append("\n".join(lines_with_no[i:i+step]).strip())

#     return chunks

# def merge_candidates(all_items):
#     seen = set()
#     merged = []
#     for it in all_items:
#         key = (it.get("page"), it.get("line_no"), it.get("start_hint"), it.get("raw"))
#         if key in seen:
#             continue
#         seen.add(key)
#         merged.append(it)
#     return merged

# all_items = []

# for page_no, page_text in split_pages(text):
#     lines_with_no = add_line_numbers(page_text)
#     chunks = chunk_by_question(lines_with_no)

#     for ch in chunks:
#         human = f"===== PAGE {page_no} =====\n{ch}"
#         messages = [
#             SystemMessage(content=system_prompt_candidate),
#             HumanMessage(content=human),
#         ]

#         raw = llm.invoke(messages).content
#         json_text = extract_first_json_object(raw)   # ✅ 여기서 유효 JSON만 잘라냄
#         obj = parser.parse(json_text)
        
#         # LogicCandidates 스키마가 {"items":[...]} 구조라고 가정
#         all_items.extend(obj.model_dump().get("items", []))

# final_obj = {"items": merge_candidates(all_items)}

# Path("output/부산연구원_상_c.json").write_text(
#     json.dumps(final_obj, indent=2, ensure_ascii=False),
#     encoding="utf-8"
# )

# print(json.dumps(final_obj, indent=2, ensure_ascii=False))


# # messages = [
# #     SystemMessage(content=system_prompt_candidate),
# #     HumanMessage(content=text)
# # ]


# # # ----- (4) 호출 + 파싱 -----
# # raw = llm.invoke(messages).content

# # try:
# #     schema_obj = parser.parse(raw)   # ValidationSchema 객체
# # except OutputParserException as e:
# #     print("파싱 실패. 원문 응답(raw)을 확인하세요.")
# #     print(raw)
# #     raise

# # print(json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False))

# # Path("output/부산연구원_상_c.json").write_text(
# #     json.dumps(schema_obj.model_dump(), indent=2, ensure_ascii=False),
# #     encoding="utf-8"
# # )


from dotenv import load_dotenv
from pathlib import Path
from schema import LogicCandidates  # LogicCandidates / LogicCandidate Pydantic 모델
import json
import re

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException
from prompts import system_prompt_candidate


load_dotenv()

# -------------------------
# LLM / Parser
# -------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

parser = PydanticOutputParser(pydantic_object=LogicCandidates)
format_instructions = parser.get_format_instructions()

system_prompt = system_prompt_candidate.format(format_instructions=format_instructions)

# -------------------------
# Utils
# -------------------------
PAGE_SPLIT_RE = re.compile(r"^===== PAGE (\d+) =====\s*$", re.MULTILINE)


def split_pages(raw: str):
    """(page_no:int, page_text:str) 리스트로 분리"""
    parts = PAGE_SPLIT_RE.split(raw)
    pages = []
    for i in range(1, len(parts), 2):
        page_no = int(parts[i])
        page_text = parts[i + 1].strip("\n")
        pages.append((page_no, page_text))
    return pages


def add_line_numbers(page_text: str) -> list[str]:
    lines = [ln.rstrip() for ln in page_text.splitlines()]
    return [f"[{i+1}] {ln}" for i, ln in enumerate(lines)]


def extract_first_json_object(s: str) -> str:
    """
    문자열에서 첫 번째 JSON 객체( {...} )만 잘라 반환.
    - 괄호 균형으로 안전하게 자름
    """
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object start '{' found")

    depth = 0
    in_str = False
    esc = False

    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]

    raise ValueError("JSON object not closed properly")


def normalize_candidate_dict(d: dict) -> dict:
    """
    LLM이 null 넣는 케이스 방지:
    - context_prev/context_next/start_hint/reason/raw/type 등 문자열 필드는 None이면 ""로
    """
    if "items" not in d or not isinstance(d["items"], list):
        return {"items": []}

    for it in d["items"]:
        if not isinstance(it, dict):
            continue

        # string fields that must be str in your schema
        for k in ("type", "start_hint", "raw", "context_prev", "context_next", "reason"):
            if it.get(k) is None:
                it[k] = ""
        # optional ints
        for k in ("page", "line_no"):
            if it.get(k) is None:
                # keep None (schema Optional[int]) OK
                pass

        # type 강제(혹시 다른 값 오면 candidate로)
        if it.get("type") != "candidate":
            it["type"] = "candidate"

    return d


def merge_candidates(items: list[dict]) -> list[dict]:
    """
    중복 제거: (page, line_no, start_hint, raw) 기준
    """
    seen = set()
    merged = []
    for it in items:
        key = (it.get("page"), it.get("line_no"), it.get("start_hint"), it.get("raw"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(it)
    return merged


# -------------------------
# Run
# -------------------------
text = Path("output/부산연구원_상.txt").read_text(encoding="utf-8")

all_items: list[dict] = []

pages = split_pages(text)

for idx, (page_no, page_text) in enumerate(pages, start=1):
    # 페이지 단위로만 호출
    lines_with_no = add_line_numbers(page_text)
    human = f"===== PAGE {page_no} =====\n" + "\n".join(lines_with_no)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human),
    ]

    try:
        raw = llm.invoke(messages).content
        json_text = extract_first_json_object(raw)

        # 1) 먼저 JSON dict로 로드
        data = json.loads(json_text)

        # 2) null/형식 보정
        data = normalize_candidate_dict(data)

        # 3) Pydantic 검증
        obj = LogicCandidates.model_validate(data)

        all_items.extend(obj.model_dump().get("items", []))

    except (ValueError, json.JSONDecodeError, OutputParserException) as e:
        print(f"[WARN] page={page_no} parse failed: {e}")
        print("----- RAW RESPONSE -----")
        print(raw if "raw" in locals() else "")
        print("------------------------")
        continue

final_obj = {"items": merge_candidates(all_items)}

out_path = Path("output/부산연구원_상_c.json")
out_path.write_text(json.dumps(final_obj, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(final_obj, indent=2, ensure_ascii=False))
print(f"\nSaved: {out_path}")