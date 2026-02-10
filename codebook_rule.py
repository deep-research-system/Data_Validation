import json
import pandas as pd
from utils.excel_save  import export_cart_xlsx
from pathlib import Path


# 파일 불러오기 및 전처리
cb = pd.read_excel("data/test.xlsx", sheet_name="codebook")

codebook_df = cb.dropna(subset=["문항"]).reset_index(drop=True)

print(codebook_df.head())

# range_items 범위 지정
def parse_options(응답: str) -> list[dict]:
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
    pairs = []
    for raw in 응답.splitlines():  # 문자열을 줄단위로 쪼개기 ex)["1: 남자", "2: 여자", "3: 기타"]
        line = raw.strip()  # 앞뒤 공백 제거
        if not line:
            continue

        # 1) 구분자 찾기: ':' 우선, 없으면 '.'
        colon_index = line.find(":")
        if colon_index == -1:     # -1의 의미 : 해당 문자를 찾지못함
            continue
    

        # 2) 구분자 앞 부분을 코드 후보로
        code_str = line[:colon_index].strip()
        label = line[colon_index + 1 :].strip()

        # 3) 숫자인 경우만 코드로 인정
        if code_str.isdigit():              # isdigit() : 문자열이 숫자로만 이루어져있는지 확인
            pairs.append({"code": int(code_str), "label": label})
            
    return pairs

# 'codes_values' 컬럼에 추출된 코드 리스트 저장
codebook_df["codes_values"] = codebook_df["응답"].apply(parse_options)

codebook_df["check_range"] = codebook_df["codes_values"].apply(bool)

codebook_df["range_min"] = codebook_df["codes_values"].apply(
    lambda x: min(o["code"] for o in x) if x else None
)
codebook_df["range_max"] = codebook_df["codes_values"].apply(
    lambda x: max(o["code"] for o in x) if x else None

)

codebook_df["check_missing"] = True
codebook_df["check_multi"] = True


# json 구조화
records = []

for r in codebook_df.itertuples(index=False):
    records.append({
        "item": r.문항,
        "question": r.질문,
        "options": r.codes_values,
    })
    
out_path = Path("data/codebook.json")
out_path.parent.mkdir(parents=True, exist_ok=True)

out_path.write_text(
    json.dumps(records, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("saved:", out_path)



# 검증 항목별 문항 리스트 생성
missing_items = codebook_df.loc[codebook_df["check_missing"], "문항"].tolist()
multiple_items = codebook_df.loc[codebook_df["check_multi"], "문항"].tolist()
range_items = codebook_df.loc[codebook_df["check_range"], "문항"].tolist()

# 검증 요약 데이터프레임 생성
summary_df = pd.DataFrame({
    "결측": [",".join(missing_items)],
    "중복응답": [",".join(multiple_items)],
    "범위": [",".join(range_items)]
})


# range 그룹 만들기 (min,max별로 같은 범위조건 문항 묶기)
g = (codebook_df.loc[codebook_df["check_range"], ["문항", "range_min", "range_max"]]    # codebook_df["check_range"] == True인 행 필터링
    .groupby(["range_min", "range_max"])["문항"]                                        # 'range_min', 'range_max' 컬럼으로 그룹화   ex) (1,5)그룹["A1", "A2"], (10,20)그룹["B1", "B2"]
    .apply(lambda s: ", ".join(s))                                                      # 그룹별 '문항'들을 쉼표로 연결된 문자열로 변환 ex) (1,5)그룹 "A1, A2", (10,20)그룹 "B1, B2"
    .reset_index(name="items"))                                                         # 인덱스를 초기화하고 'items'라는 이름의 컬럼으로 결과 저장
print("범위 그룹화 결과:\n", g)

# dict 하나 = 엑셀 한컬럼 형태로 넣을 수 있게 튜플형으로 변경
range_columns = [{
        "title": "범위",
        "items": r.items,
        "values": f"{int(r.range_min)}, {int(r.range_max)}"}
    for r in g.itertuples(index=False)              # itertuples : DataFrame의 각 행을 튜플로 반환
]

print("범위 컬럼들:\n", range_columns)

columns = [
    {"title": "결측", "items": ",".join(missing_items), "values": ""},
    {"title": "중복 응답", "items": ",".join(multiple_items), "values": ""},
] + range_columns


out = export_cart_xlsx(
    columns=columns,
    out_path="data/validation_cart.xlsx",
    start_col=1,  # A부터
)
print("saved:", out)