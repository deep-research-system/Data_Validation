import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# ①②③... 같은 동그라미 숫자 → "1","2","3"으로
CIRCLED_NUM = {
    "⓪": "0",
    "①": "1",
    "②": "2",
    "③": "3",
    "④": "4",
    "⑤": "5",
    "⑥": "6",
    "⑦": "7",
    "⑧": "8",
    "⑨": "9",
    "⑩": "10",
    "⑪": "11",
    "⑫": "12",
    "⑬": "13",
    "⑭": "14",
    "⑮": "15",
    "⑯": "16",
    "⑰": "17",
    "⑱": "18",
    "⑲": "19",
    "⑳": "20",
    "㉑": "21",
    "㉒": "22",
    "㉓": "23",
    "㉔": "24",
    "㉕": "25",
    "㉖": "26",
    "㉗": "27",
    "㉘": "28",
    "㉙": "29",
    "㉚": "30",
    "㉛": "31",
    "㉜": "32",
    "㉝": "33",
    "㉞": "34",
    "㉟": "35",
    "㊱": "36",
    "㊲": "37",
    "㊳": "38",
    "㊴": "39",
    "㊵": "40",
    "㊶": "41",
    "㊷": "42",
    "㊸": "43",
    "㊹": "44",
    "㊺": "45",
    "㊻": "46",
    "㊼": "47",
    "㊽": "48",
    "㊾": "49",
    "㊿": "50",
}


def circled_to_code(s: str) -> Optional[str]:
    s = s.strip()
    return CIRCLED_NUM.get(s)


def norm(s: str) -> str:
    # NBSP 등 정리 + 공백 정리
    s = s.replace("\u00a0", " ")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


# "⇒ A4-1. 이동" / "▶B2로 이동" / "(→ A5 이동)" 등에서 타겟 ID 추출 (단일 매칭)
GOTO_RE = re.compile(
    r"(?:⇒|▶|→|->)\s*([A-Za-z]\d+(?:-\d+)?)\s*(?:\.?\s*(?:로)?\s*이동)?"
)

# 한 줄에 여러 개 나오는 경우용(전체 추출)
GOTO_ALL_RE = re.compile(r"(?:⇒|▶|→|->)\s*([A-Za-z]\d+(?:-\d+)?)")

# 문항 헤더: "## A4. ..." 또는 "A4. ..." 둘 다 대응
Q_HEADER_RE = re.compile(r"^(?:##\s*)?([A-Za-z]\d+(?:-\d+)?)\.\s*(.+?)\s*$")

# 옵션 라인: "- ① 전혀 아니다" or "① 전혀 아니다"
OPT_RE = re.compile(
    r"^(?:-\s*)?([⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑-㊿])\s*(.+?)\s*$"
)


def detect_question_type(question_text: str, options: List[Dict[str, Any]]) -> str:
    # 아주 단순 휴리스틱: 옵션이 있으면 single_choice로 두고,
    # "(해당 항목 모두 선택)" 같은 문구가 있으면 multi로 바꿀 수 있음
    if options:
        if "모두 선택" in question_text or "복수" in question_text:
            return "multi_choice"
        return "single_choice"
    return "text"


def parse_md_survey(md_text: str) -> Dict[str, Any]:
    lines = [norm(l) for l in md_text.split("\n")]
    lines = [l for l in lines if l != ""]  # 빈줄 제거 (너무 공격적이면 주석 처리)

    survey: Dict[str, Any] = {"title": None, "questions": []}

    current_q: Optional[Dict[str, Any]] = None
    last_option: Optional[Dict[str, Any]] = None

    # 현재 문항에서 "옵션 N개 + 로직 N개(한 줄에 묶임)" 케이스를 처리하기 위해
    # 문항별로 로직 라인에서 goto 후보를 모아 둠
    pending_gotos: List[str] = []

    def apply_pending_gotos_if_possible():
        """
        문항 블록 내에서:
        - 옵션이 여러 개 쌓여 있고
        - 로직 goto도 여러 개 쌓였고
        - len(options) == len(pending_gotos)이면
        옵션 순서대로 goto를 매핑한다.
        """
        nonlocal pending_gotos, current_q
        if not current_q:
            return
        opts = current_q["options"]
        if not opts:
            return
        if pending_gotos and len(opts) == len(pending_gotos):
            for opt, to in zip(opts, pending_gotos):
                if opt.get("goto") is None:
                    opt["goto"] = to
            pending_gotos = []

    def flush_question():
        nonlocal current_q, pending_gotos
        if not current_q:
            return

        # flush 직전에, 혹시 "한 줄에 묶인 로직"이 옵션 수와 딱 맞게 모였으면 반영
        apply_pending_gotos_if_possible()

        # 남아있는 pending_gotos가 있는데 옵션 수와 다르면: 최소한 앞에서부터 채워넣기(보수적)
        if pending_gotos and current_q["options"]:
            n = min(len(current_q["options"]), len(pending_gotos))
            for i in range(n):
                if current_q["options"][i].get("goto") is None:
                    current_q["options"][i]["goto"] = pending_gotos[i]
            pending_gotos = []

        # type 자동 결정
        current_q["type"] = detect_question_type(current_q["text"], current_q["options"])
        survey["questions"].append(current_q)
        current_q = None

    for line in lines:
        # 문항 시작 감지
        m_q = Q_HEADER_RE.match(line)
        if m_q:
            flush_question()
            qid, qtext = m_q.group(1), m_q.group(2)
            current_q = {"id": qid, "text": qtext, "type": "unknown", "options": []}
            last_option = None
            pending_gotos = []
            continue

        if not current_q:
            # 타이틀은 처음 나오는 H1/큰 제목을 쓰고 싶으면 여기서 커스터마이즈
            if survey["title"] is None and len(line) <= 40 and not line.startswith("|"):
                survey["title"] = line
            continue

        # 옵션 감지
        m_opt = OPT_RE.match(line)
        if m_opt:
            circled, label = m_opt.group(1), m_opt.group(2)
            code = circled_to_code(circled) or circled
            opt = {"code": code, "label": label, "goto": None}
            current_q["options"].append(opt)
            last_option = opt

            # 옵션 라인 자체에 goto가 붙어있으면 바로 추출
            g = GOTO_RE.search(line)
            if g:
                last_option["goto"] = g.group(1)

            # 옵션을 하나 추가했으니, pending_gotos가 이미 옵션 수만큼 모여있는지 확인
            apply_pending_gotos_if_possible()
            continue

        # ===== 로직 라인 처리 =====
        # 케이스1) 옵션 바로 다음줄에 "⇒ A4-1 이동" 같은게 한 개만 내려오는 경우
        # 케이스2) 한 줄에 "(⇒ A4-1 이동) (⇒ A5 이동) ..."처럼 여러 개가 묶여 나오는 경우
        if "⇒" in line or "▶" in line or "→" in line or "->" in line or "이동" in line:
            gotos_in_line = GOTO_ALL_RE.findall(line)

            if gotos_in_line:
                # 2) 여러개면 pending에 누적(옵션 수와 같아지는 순간 매핑)
                if len(gotos_in_line) >= 2:
                    pending_gotos.extend(gotos_in_line)
                    apply_pending_gotos_if_possible()
                    continue

                # 1) 한 개면 기존 방식(직전 옵션에 붙이기)
                if last_option and last_option.get("goto") is None and len(gotos_in_line) == 1:
                    last_option["goto"] = gotos_in_line[0]
                    continue

        # 옵션 라벨이 여러 줄로 끊긴 케이스(라벨 이어붙이기)
        if last_option and not Q_HEADER_RE.match(line) and not OPT_RE.match(line):
            # 이동 표기만 있는 줄은 위에서 처리했으니, 여기서는 일반 텍스트만 붙임
            if not ("이동" in line and GOTO_RE.search(line)):
                if not line.startswith("|") and not line.startswith("<!--"):
                    last_option["label"] = (last_option["label"] + " " + line).strip()

    flush_question()

    if survey["title"] is None:
        survey["title"] = "설문지"

    return survey


if __name__ == "__main__":
    in_path = Path("data/pdf_markdown/pdf_test2.md")  # 필요 시 변경
    md = in_path.read_text(encoding="utf-8")
    result = parse_md_survey(md)

    out_path = in_path.with_suffix(".json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {out_path}")
    print(f"questions: {len(result['questions'])}")
