import re
from pathlib import Path

# ----------------------------
# 설정
# ----------------------------

TXT_PATH = "output/pdf_text(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.txt"

# 문항 ID 패턴 (A37, Q2-1, C4 등)
QUESTION_PATTERN = re.compile(r'^([A-Z]\d+(?:-\d+)?)\.')

# 로직 관련 키워드 패턴
LOGIC_PATTERN = re.compile(
    r'(⇒|이동|응답|건너|설문\s*종료)',
    re.IGNORECASE
)

# ----------------------------
# 텍스트 로드
# ----------------------------

text = Path(TXT_PATH).read_text(encoding="utf-8")
lines = text.splitlines()

candidates = []

current_question = None

# ----------------------------
# 라인 단위 스캔
# ----------------------------

for idx, line in enumerate(lines, start=1):

    stripped = line.strip()

    # 1️⃣ 문항 ID 갱신
    q_match = QUESTION_PATTERN.match(stripped)
    if q_match:
        current_question = q_match.group(1)

    # 2️⃣ 로직 후보 탐지
    if LOGIC_PATTERN.search(stripped):

        candidates.append({
            "line_no": idx,
            "question": current_question,
            "text": stripped
        })

# ----------------------------
# 출력
# ----------------------------

print("총 후보 개수:", len(candidates))

for c in candidates[:20]:  # 처음 20개만 확인
    print(c)
