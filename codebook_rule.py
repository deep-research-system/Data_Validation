import pandas as pd
import re
from typing import Any, Dcit, List, Tuple


###############################################
# # 헤더가 컬럼 아닐시
# ###############################################
# #엑셀 불러오기
# cb_raw = pd.read_excel("data/test.xlsx", sheet_name="codebook", header=None)

# # 헤더후보 탐색
# target = {"문항", "질문", "응답"}
# header_row = None
# print(cb_raw.head(5))
# for i in range(len(cb_raw)):
#     row_vals = set(cb_raw.iloc[i].dropna().astype(str).str.strip().tolist())
#     if target.issubset(row_vals):
#         header_row = i
#         break

# # 해당 행을 header로 재로드
# cb_header = pd.read_excel("data/test.xlsx", sheet_name="codebook", header=header_row)
# cb_header.columns = cb_header.columns.map(lambda x: str(x).strip())

# cb = cb_header[["문항", "질문", "응답"]].rename(columns={
#     "문항": "item",
#     "질문": "question",
#     "응답": "options"
# })
# print(cb.head(5))



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

