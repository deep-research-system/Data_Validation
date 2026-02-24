import pandas as pd

# 파일 불러오기 및 전처리
codebook = pd.read_excel("src/data/test.xlsx", sheet_name="codebook")

codebook_df = codebook.dropna(subset=["문항"]).reset_index(drop=True)


# 응답 컬럼에서 선택지 코드만 추출하여 min, max 계산
def parse_minmax(option_text):
    """
    설문지 응답에서 선택지 코드의 최소값과 최대값을 추출하는 함수
    Args:
        option_text (str): 응답 문자열 (예: "1: 남자\n2: 여자\n3: 기타")
    Returns:
        min_code, max_code : 선택지 코드의 최소값과 최대값
    """
    
    codes = []
    
    for raw in str(option_text).splitlines():
        line = raw.strip()
        if not line:
            continue
        
        # ':' 기준으로 분리
        colon_index = line.find(":")
        if colon_index == -1:
            continue
        
        code_str = line[:colon_index].strip()
        if code_str.isdigit():
            codes.append(int(code_str))
        
    if not codes:
        return None, None
    return min(codes), max(codes)
        


# range_min, range_max 바로 생성
range_min_list = []
range_max_list = []

# 응답 컬럼에서 선택지 코드의 최소값과 최대값을 추출하여 리스트에 저장
for response in codebook_df["응답"]:
    min_val, max_val = parse_minmax(response)
    range_min_list.append(min_val)
    range_max_list.append(max_val)

codebook_df["range_min"] = range_min_list
codebook_df["range_max"] = range_max_list

# range 존재 여부
codebook_df["check_range"] = codebook_df["range_min"].notna()

# 결측 / 중복은 기본 True
codebook_df["check_missing"] = True
codebook_df["check_multi"] = True


# 범위 컬럼값 생성
range_map = {}  # (range_min, range_max) -> [문항들]

# 각 행을 순회하며 범위 조건이 있는 문항들을 그룹화
for _, row in codebook_df.iterrows():       # df.itterrows(): 각 행을 하나씩 꺼내서 처리
    if pd.isna(row["range_min"]):
        continue
    
    key = (row["range_min"], row["range_max"])

    if key not in range_map:            # key가 없으면 새 리스트 생성
        range_map[key] = []

    range_map[key].append(str(row["문항"])) # 문항을 문자열로 변환하여 추가

rule_culumns = []



# 결측 컬럼값 생성
missing_items = codebook_df.loc[codebook_df["check_missing"], "문항"].astype(str).tolist()
rule_culumns.append({
    "title": "결측",
    "items": ", ".join(missing_items),
    "values": ""
})

# 중복응답 컬럼값 생성
multiple_items = codebook_df.loc[codebook_df["check_multi"], "문항"].astype(str).tolist()
rule_culumns.append({
    "title": "중복응답",
    "items": ", ".join(multiple_items),
    "values": ""
})

# 범위 컬럼값 생성
for (range_min, range_max), range_items in range_map.items():  # range_map의 각 (min,max)키와 해당 문항 리스트를 순회
    rule_culumns.append({
        "title": "범위",
        "items": ", ".join(range_items),
        "values": f"{int(range_min)}, {int(range_max)}"
    })


# 출력용 데이터프레임 생성
df = pd.DataFrame(rule_culumns)

# 엑셀로 저장(INDEX, HEADER 없음, 행열 반전)
df.transpose().to_excel("src/output/validation_cart.xlsx", index=False, header=False)