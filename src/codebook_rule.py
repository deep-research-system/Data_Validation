import pandas as pd


# 파일 불러오기 및 전처리
cb = pd.read_excel("data/test.xlsx", sheet_name="codebook")

codebook_df = cb.dropna(subset=["문항"]).reset_index(drop=True)

print(codebook_df.head())

##############################
# 응답 컬럼 파싱
##############################

# 응답 문자열에서 선택지 코드 추출 함수
def parse_codes(options_text: str) -> list[int]:
    """
    응답 문자열에서 선택지 코드를 추출하는 함수
    Args:
        options_text (str): 응답 문자열 (예: "1: 남자\n2: 여자\n3: 기타")`
    Returns:
        list[int]: 추출된 선택지 코드 리스트
    """
    
    codes = []
    for raw in options_text.splitlines():  # 문자열을 줄단위로 쪼개기 ex)["1: 남자", "2: 여자", "3: 기타"]
        line = raw.strip()  # 앞뒤 공백 제거
        if not line:
            continue

        # 1) 구분자 찾기: ':' 우선, 없으면 '.'
        colon_index = line.find(":")
        if colon_index == -1:     # -1의 의미 : 해당 문자를 찾지못함
            continue
    

        # 2) 구분자 앞 부분을 코드 후보로
        code_str = line[:colon_index].strip()

        # 3) 숫자인 경우만 코드로 인정
        if code_str.isdigit():              # isdigit() : 문자열이 숫자로만 이루어져있는지 확인
            codes.append(int(code_str))
            
    return codes

# 'codes_values' 컬럼에 추출된 코드 리스트 저장
codebook_df["codes_values"] = codebook_df["응답"].apply(parse_codes)

codebook_df["check_range"] = codebook_df["codes_values"].apply(bool)

################################
# 범위 조건 생성 및 저장
################################

range_min_list = []
range_max_list = []

# 각 문항별로 min, max 코드값 계산
for codes in codebook_df["codes_values"]:
    if not codes:
        range_min_list.append(None)
        range_max_list.append(None)
        continue


    range_min_list.append(min(codes))
    range_max_list.append(max(codes))
    
codebook_df["range_min"] = range_min_list
codebook_df["range_max"] = range_max_list


codebook_df["check_missing"] = True
codebook_df["check_multi"] = True


# 범위 컬럼값 생성
range_map = {}  # (range_min, range_max) -> [문항들]

# 각 행을 순회하며 범위 조건이 있는 문항들을 그룹화
for _, row in codebook_df.iterrows():       # df.itterrows(): 각 행을 하나씩 꺼내서 처리
    if not row["check_range"]:              # check_range가 False인 행은 건너뜀
        continue

    key = (row["range_min"], row["range_max"])

    if key not in range_map:            # key가 없으면 새 리스트 생성
        range_map[key] = []

    range_map[key].append(str(row["문항"])) # 문항을 문자열로 변환하여 추가

rule_culumns = []


##########################
# 컬럼갑 생성
##########################

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


###############################
# 출력용 데이터프레임 생성
###############################

df = pd.DataFrame(rule_culumns)

# 엑셀로 저장(INDEX, HEADER 없음, 행열 반전)
df.transpose().to_excel("output/validation_cart.xlsx", index=False, header=False)