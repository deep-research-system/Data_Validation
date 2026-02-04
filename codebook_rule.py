import pandas as pd
import re
from typing import Any, Optional, List, Tuple


# 파일 불러오기 및 전처리
cb = pd.read_excel("data/test.xlsx", sheet_name="codebook")

codebook_df = cb[["문항", "응답"]].dropna(subset=["문항"]).reset_index(drop=True)

# range_items 범위 지정
def extract_codes(응답: str) -> list[int]:
    """
    코드북의 '응답' 문자열에서 선택지 코드를 추출한다.

    매개변수:
        응답 (str): 코드북의 '응답' 컬럼 문자열.
                   예: "1: 남자\\n2: 여자\\n3: 기타"

    반환값:
        list[int]:
            - 형식이 올바른 경우: 추출된 정수 코드들의 리스트   예: [1, 2, 3]
            - 형식이 올바르지 않은 경우: 빈 리스트 []          (범위 검증 대상 아님을 의미)
            
    내부 변수
        line (str): 줄 단위로 분리된 응답 문자열의 한 행.
        colon_index (int): line 문자열에서 첫 번째 ':' 문자가 등장하는 위치(index).
        code_str (str): line에서 ':' 이전 부분을 잘라낸 문자열.
        code_values (list[int]): 형식 검증을 통과한 정수 코드들을 누적 저장하는 리스트.
    """
    code_values = []
    for raw in 응답.splitlines():  # 문자열을 줄단위로 쪼개기 ex)["1: 남자", "2: 여자", "3: 기타"]
        line = raw.strip()  # 앞뒤 공백 제거
        if not line:
            continue

        # 1) 구분자 찾기: ':' 우선, 없으면 '.'
        colon_index = line.find(":")
        if colon_index == -1:     # -1의 의미 : 해당 문자를 찾지못함
            return []

        # 2) 구분자 앞 부분을 코드 후보로
        code_str = line[:colon_index].strip()

        # 3) 숫자인 경우만 코드로 인정
        if code_str.isdigit():              # isdigit() : 문자열이 숫자로만 이루어져있는지 확인
            code_values.append(int(code_str))

    return code_values

# 'codes_values' 컬럼에 추출된 코드 리스트 저장
codebook_df["codes_values"] = codebook_df["응답"].apply(extract_codes)

codebook_df["check_range"] = codebook_df["codes_values"].apply(bool)

codebook_df["range_min"] = codebook_df["codes_values"].apply(
    lambda x: min(x) if x else None
)
codebook_df["range_max"] = codebook_df["codes_values"].apply(
    lambda x: max(x) if x else None
)

codebook_df["check_missing"] = True
codebook_df["check_multi"] = True


# 검증 항목별 문항 리스트 생성
missing_items = codebook_df.loc[codebook_df["check_missing"], "문항"].tolist()
multiple_items = codebook_df.loc[codebook_df["check_multi"], "문항"].tolist()
range_items = codebook_df.loc[codebook_df["check_range"], "문항"].tolist()






print(codebook_df[["문항", "codes_values", "check_range", "range_min", "range_max"]].head())
print(
    codebook_df.loc[
        codebook_df["문항"] == "B2",
        ["문항", "codes_values", "check_range", "range_min", "range_max"]
    ]
)

# 검증 요약 데이터프레임 생성
summary_df = pd.DataFrame({
    "결측": [",".join(missing_items)],
    "중복응답": [",".join(multiple_items)],
    "범위": [",".join(range_items)]
})



# 검증 요약 엑셀 저장
summary_df.to_excel("data/validation_summary.xlsx", index=False)




















######################
# 옵션 문자열 파싱
######################
# "1: 라벨 ... 2: 라벨 ..." 형태를 연속 문자열에서도 잡아내는 패턴
# CODE_LABEL_PATTERN = re.compile(
#     r"""
#     (?P<code>\d+)          # 1,2,10...
#     \s*[:\.]\s*            # ":" 또는 "." (혹시 1.  라벨도 대응)
#     (?P<label>.*?)         # 라벨 (lazy)
#     (?=                    # 다음 코드 시작이거나 문자열 끝
#         \s*\d+\s*[:\.]
#         | \Z
#     )
#     """,
#     re.VERBOSE | re.DOTALL
# )

# def norm_space(s: str) -> str:
#     """문자열 정규화 함수

#     Args:
#         s (str): 정규화할 문자열
#     Returns:
#         str: 정규화된 문자열
#     """
#     s = s.replace("\u00a0", " ")                 # NBSP(줄바꿈 되지않는 공백)
#     s = re.sub(r"[ \t]+", " ", s)                 # 여러 공백/탭 -> 한칸 공백
#     s = re.sub(r"\n{2,}", "\n", s)                # 여러 줄바꿈 -> 한줄바꿈
#     return s.strip()                              # 앞뒤 공백 제거


# def parse_options(options: Any) -> List[int]:
#     """
#     returns:
#       - allowed_codes: List[int]

#     options가 NaN/None이rjsk
#     코드-라벨 패턴이 없으면 [] 반환
#     """
#     if options is None or (isinstance(options, float) and pd.isna(options)):
#         return []

#     text = norm_space(str(options))

#     matches = list(CODE_LABEL_PATTERN.finditer(text))
#     if not matches:
#         return []

#     allowed_codes: List[int] = []

#     for m in matches:
#         code_str = m.group("code").strip()
#         allowed_codes.append(int(code_str))

#     # 중복 제거 + 정렬
#     allowed_codes = sorted(set(allowed_codes))

#     return allowed_codes


# def range_from_allowed_codes(allowed_codes: List[int]) -> Optional[Tuple[int, int]]:
#     """
#     allowed_codes가 있으면 (min, max) 반환
#     없으면 None
#     """
#     if not allowed_codes:
#         return None

#     return min(allowed_codes), max(allowed_codes)

# #########################
# # between_a_b 룰 생성
# # 현재는 범주형만 만듬, 숫자형도 범위로 표현해야하면 따로 만들듯
# #########################
# def build_between_rule(item: str, allowed_codes: List[int]) -> Optional[dict]:
#     if not allowed_codes:
#         return None

#     return {
#         "rule_type": "between_a_b",
#         "source": "codebook",
#         "min": min(allowed_codes),
#         "max": max(allowed_codes),
#         "inclusive_min": True,
#         "inclusive_max": True,
#     }

# ########################
# # 테스트 함수
# ########################
# def test_between_rules(cb: pd.DataFrame, limit: int = 50) -> pd.DataFrame:
#     """
#     codebook df(cb)에서
#     options -> allowed_codes 파싱
#     allowed_codes -> between_a_b rule 생성
#     결과를 DataFrame으로 반환
#     """
#     rows = []
#     for _, r in cb.iterrows():
#         item = str(r["item"]).strip()
#         options = r.get("options")

#         codes = parse_options(options)
#         rule = build_between_rule(item, codes)

#         if rule is None:
#             continue

#         rows.append({
#             "item": item,
#             "codes_count": len(codes),
#             "allowed_codes_preview": codes[:10],
#             "min": rule["min"],
#             "max": rule["max"],
#             "inclusive_min": rule["inclusive_min"],
#             "inclusive_max": rule["inclusive_max"],
#         })

#     df = pd.DataFrame(rows).sort_values(["item"]).reset_index(drop=True)

#     if limit is not None and len(df) > limit:
#         return df.head(limit)
#     return df


# # ---- 실행 ----
# between_df = test_between_rules(cb, limit=50)

# print("between_a_b 생성된 문항 수:", len(between_df))
# print(between_df.to_string(index=False))

