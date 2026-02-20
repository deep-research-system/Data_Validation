from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple


# ----------------------------
# 패턴 정의 (후보 추출)
# ----------------------------

TRIGGER_RE = re.compile(r"(☞|⇒|->|→|로\s*이동|건너뛰기|skip)", re.IGNORECASE)
PAREN_EXPAND_RE = re.compile(r"\(\s*☞\s*①")  # "(☞ ① ...)" 보기확장 오탐 제거
DISPLAY_NOISE_RE = re.compile(r"(모두\s*표시|표시해\s*주세요|해당\s*사항\s*모두\s*표시|기입)", re.IGNORECASE)

MOVE_TARGET_RE = re.compile(
    r"""
    (?:
        (문\s*\d+(?:-\d+)*|[A-Za-z]\d+(?:-\d+)*|\d+(?:-\d+)*)
        (?:\s*~\s*
            (문\s*\d+(?:-\d+)*|[A-Za-z]\d+(?:-\d+)*|\d+(?:-\d+)*)
        )?
    )
    """,
    re.VERBOSE,
)

QID_LINE_RE = re.compile(r"^\s*(문\s*\d+(?:-\d+)*|\d+(?:-\d+)*|[A-Za-z]\d+(?:-\d+)*)\s*[\.\)]?")


@dataclass
class SkipCandidate:
    line_no: int
    start_col: Optional[str]
    trigger_line: str
    context: str
    targets: List[str]


def _normalize_qid(raw: str) -> str:
    return re.sub(r"\s+", "", raw)


def _find_nearest_qid(lines: List[str], idx: int, lookback: int = 40) -> Optional[str]:
    """
    idx 라인 위로 올라가며 가장 가까운 문항 ID를 찾는다.
    """
    for j in range(idx, max(-1, idx - lookback), -1):
        m = QID_LINE_RE.search(lines[j])
        if m:
            return _normalize_qid(m.group(1))
    return None


def extract_skip_candidates(text: str, *, context_lines: int = 2, lookback_qid: int = 40) -> List[SkipCandidate]:
    lines = text.splitlines()
    out: List[SkipCandidate] = []

    for i, line in enumerate(lines):
        raw = line.strip()
        if not raw:
            continue

        if not TRIGGER_RE.search(raw):
            continue

        # 보기확장 오탐 제거
        if PAREN_EXPAND_RE.search(raw):
            continue

        # "모두 표시"류 오탐 제거 (단, 명시적 이동이 있으면 유지)
        if DISPLAY_NOISE_RE.search(raw) and not re.search(r"(로\s*이동|⇒)", raw):
            continue

        # 이동 대상 추출
        targets: List[str] = []
        for m in MOVE_TARGET_RE.finditer(raw):
            t1, t2 = m.group(1), m.group(2)
            if t1:
                targets.append(_normalize_qid(t1))
            if t2:
                targets.append(_normalize_qid(t2))

        # ☞만 있고 대상도 없고 '로 이동'도 없으면 제거
        if not targets and not re.search(r"(로\s*이동|건너뛰기)", raw):
            continue

        start_col = _find_nearest_qid(lines, i, lookback=lookback_qid)

        s = max(0, i - context_lines)
        e = min(len(lines), i + context_lines + 1)
        context = "\n".join(lines[s:e]).strip()

        out.append(
            SkipCandidate(
                line_no=i + 1,
                start_col=start_col,
                trigger_line=raw,
                context=context,
                targets=targets,
            )
        )

    return out


# ----------------------------
# 문항 블록 묶기 + LLM 입력 생성
# ----------------------------

@dataclass
class QuestionBlock:
    qid: str
    candidates: List[SkipCandidate]
    merged_text: str   # LLM에 넣을 "문항 블록"


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def group_candidates_by_qid(cands: List[SkipCandidate]) -> Dict[str, List[SkipCandidate]]:
    grouped: Dict[str, List[SkipCandidate]] = {}
    for c in cands:
        if not c.start_col:
            # 문항ID 추정 실패면 스킵(원하면 "UNKNOWN"으로 모아도 됨)
            continue
        grouped.setdefault(c.start_col, []).append(c)
    return grouped


def build_question_blocks(
    grouped: Dict[str, List[SkipCandidate]],
    *,
    include_line_numbers: bool = True,
    max_lines_per_block: int = 10,
) -> List[QuestionBlock]:
    """
    같은 qid에 대한 후보들을 합쳐서 LLM에 주기 좋은 블록으로 만든다.
    - merged_text는 과도하게 길어지지 않게 제한
    """
    blocks: List[QuestionBlock] = []

    # qid 정렬: 숫자/문/알파 혼재라 단순 정렬(문서 순서 유지하려면 line_no 기반 정렬 추천)
    # 여기선 '최초 등장 line_no' 기준으로 정렬
    qid_with_first_line: List[Tuple[str, int]] = []
    for qid, items in grouped.items():
        first_line = min(x.line_no for x in items)
        qid_with_first_line.append((qid, first_line))
    qid_with_first_line.sort(key=lambda x: x[1])

    for qid, _ in qid_with_first_line:
        items = sorted(grouped[qid], key=lambda x: x.line_no)

        # context들을 합치되 중복 제거(동일 문맥 반복 방지)
        contexts = _dedupe_preserve_order([it.context for it in items if it.context.strip()])

        # 너무 길면 자르기: 문맥을 line 단위로 합치고 상한 적용
        merged_lines: List[str] = []
        for ctx in contexts:
            for ln in ctx.splitlines():
                if ln.strip():
                    merged_lines.append(ln.rstrip())
            merged_lines.append("")  # 문맥 구분 공백

        # 블록 헤더 + 후보 라인 요약
        header = [f"[문항ID] {qid}"]
        if include_line_numbers:
            trigger_summ = [
                f"- L{it.line_no}: {it.trigger_line}"
                for it in items
            ]
        else:
            trigger_summ = [f"- {it.trigger_line}" for it in items]

        # merged_text 구성
        body = ["[이동지시 라인]"] + trigger_summ + ["", "[원문 컨텍스트]"] + merged_lines

        # 길이 제한(라인 수 기준)
        if max_lines_per_block is not None and len(body) > max_lines_per_block:
            body = body[:max_lines_per_block] + ["...(생략)"]

        merged_text = "\n".join(body).strip()

        blocks.append(QuestionBlock(qid=qid, candidates=items, merged_text=merged_text))

    return blocks


def build_llm_input_from_blocks(
    blocks: List[QuestionBlock],
    *,
    doc_title: str = "SKIP LOGIC CANDIDATE BLOCKS",
) -> str:
    """
    여러 문항 블록을 하나의 텍스트로 합쳐 LLM 입력으로 만든다.
    """
    parts: List[str] = [f"=== {doc_title} ==="]
    for b in blocks:
        parts.append(b.merged_text)
        parts.append("\n---\n")
    return "\n".join(parts).strip()


# ----------------------------
# 파일 실행 예시
# ----------------------------
if __name__ == "__main__":
    txt_path = r"output/요양시설_중상.txt"  # 네 실제 경로로 수정
    text = Path(txt_path).read_text(encoding="utf-8", errors="replace")

    cands = extract_skip_candidates(text, context_lines=2, lookback_qid=40)
    grouped = group_candidates_by_qid(cands)
    blocks = build_question_blocks(grouped, include_line_numbers=True, max_lines_per_block=80)

    llm_input = build_llm_input_from_blocks(blocks, doc_title="요양시설_중상 스킵 후보 블록")

    out_path = Path("skip_blocks_for_llm.txt")
    out_path.write_text(llm_input, encoding="utf-8")
    print(f"후보 {len(cands)}개 → 문항블록 {len(blocks)}개")
    print(f"LLM 입력 파일 저장: {out_path.resolve()}")