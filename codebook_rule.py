import pandas as pd
import re
from typing import Any, Optional, List, Tuple


####################
# 파일 불러오기 및 전처리
####################
path = "data/test.xlsx"

def load_codebook(path):
    """
    코드북 불러오기 및 columns rename
    
    :param path: codebook 파일경로
    """
    cb = pd.read_excel(path, sheet_name="codebook", header=0)
    cb = cb.rename(columns={
        "문항": "item",
        "질문": "question",
        "응답": "options"
    })

    cb = cb[["item", "question", "options"]]
    cb = cb.dropna(subset=["item"])
    cb["item"] = cb["item"].astype(str).str.strip()

    return cb

cb = load_codebook(path)

print(cb.head)



######################
# 옵션 문자열 파싱
######################
# "1: 라벨 ... 2: 라벨 ..." 형태를 연속 문자열에서도 잡아내는 패턴
# split이나 slice로 파싱시 10개 이상 항목시 깨짐, 라벨에 숫자있을시 깨짐 등의 문제발생생
CODE_LABEL_PATTERN = re.compile(
    r"""
    (?P<code>\d+)          # 1,2,10...
    \s*[:\.]\s*            # ":" 또는 "." (혹시 1.  라벨도 대응)
    (?P<label>.*?)         # 라벨 (lazy)
    (?=                    # 다음 코드 시작이거나 문자열 끝
        \s*\d+\s*[:\.]
        | \Z
    )
    """,
    re.VERBOSE | re.DOTALL
)

def norm_space(s: str) -> str:
    """문자열 정규화 함수

    Args:
        s (str): 정규화할 문자열
    Returns:
        str: 정규화된 문자열
    """
    s = s.replace("\u00a0", " ")                 # NBSP(줄바꿈 되지않는 공백)
    s = re.sub(r"[ \t]+", " ", s)                 # 여러 공백/탭 -> 한칸 공백
    s = re.sub(r"\n{2,}", "\n", s)                # 여러 줄바꿈 -> 한줄바꿈
    return s.strip()                              # 앞뒤 공백 제거


def parse_options(options: Any) -> List[int]:
    """
    returns:
      - allowed_codes: List[int]

    options가 NaN/None이rjsk
    코드-라벨 패턴이 없으면 [] 반환환
    """
    if options is None or (isinstance(options, float) and pd.isna(options)):
        return []

    text = norm_space(str(options))

    matches = list(CODE_LABEL_PATTERN.finditer(text))
    if not matches:
        return []

    allowed_codes: List[int] = []

    for m in matches:
        code_str = m.group("code").strip()
        allowed_codes.append(int(code_str))

    # 중복 제거 + 정렬
    allowed_codes = sorted(set(allowed_codes))

    return allowed_codes


def range_from_allowed_codes(allowed_codes: List[int]) -> Optional[Tuple[int, int]]:
    """
    allowed_codes가 있으면 (min, max) 반환
    없으면 None
    """
    if not allowed_codes:
        return None

    return min(allowed_codes), max(allowed_codes)

#########################
# between_a_b 룰 생성
# 현재는 범주형만 만듬, 숫자형도 범위로 표현해야하면 따로 만들듯듯
#########################
def build_between_rule(item: str, allowed_codes: List[int]) -> Optional[dict]:
    if not allowed_codes:
        return None

    return {
        "rule_type": "between_a_b",
        "source": "codebook",
        "confidence": 0.8,   # 임시값
        "min": min(allowed_codes),
        "max": max(allowed_codes),
        "inclusive_min": True,
        "inclusive_max": True,
    }

########################
# 테스트 함수
########################
def test_between_rules(cb: pd.DataFrame, limit: int = 50) -> pd.DataFrame:
    """
    codebook df(cb)에서
    options -> allowed_codes 파싱
    allowed_codes -> between_a_b rule 생성
    결과를 DataFrame으로 반환
    """
    rows = []
    for _, r in cb.iterrows():
        item = str(r["item"]).strip()
        options = r.get("options")

        codes = parse_options(options)
        rule = build_between_rule(item, codes)

        if rule is None:
            continue

        rows.append({
            "item": item,
            "codes_count": len(codes),
            "allowed_codes_preview": codes[:10],
            "min": rule["min"],
            "max": rule["max"],
            "inclusive_min": rule["inclusive_min"],
            "inclusive_max": rule["inclusive_max"],
        })

    df = pd.DataFrame(rows).sort_values(["item"]).reset_index(drop=True)

    if limit is not None and len(df) > limit:
        return df.head(limit)
    return df


# ---- 실행 ----
between_df = test_between_rules(cb, limit=50)

print("between_a_b 생성된 문항 수:", len(between_df))
print(between_df.to_string(index=False))

