from pathlib import Path
import os
import json

from openai import OpenAI
from prompts import logic_prompt
from schema import skip_logic_schema

md_path = Path("output_markdown/가족보호자_임종기돌봄 설문지(최종)_심층인터뷰 추가_중.md")

def logic_llm():
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    md = md_path.read_text(encoding="utf-8")

    llm_answer = client.responses.create(
        model="gpt-5-nano",
        input=[
            {"role": "system", "content": logic_prompt},
            {"role": "user", "content": md},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": skip_logic_schema["name"],
                "schema": skip_logic_schema["schema"],
                "strict": skip_logic_schema.get("strict", True),
            }
        },
    )

    text = llm_answer.output_text.strip()
    llm_json =json.loads(text)
    data = llm_json["items"]

    print("\n=== 이동 로직 결과 ===\n")
    for a in data:
        print(a)

if __name__ == "__main__":
    logic_llm()































# def to_excel(rows: list[dict]) -> None:
#     wb = Workbook()
#     ws = wb.active
#     ws.title = "skip"

#     col = 1  # A열부터

#     for it in rows:
#         start = (it.get("start") or "").strip()
#         end = (it.get("end") or "").strip()
#         value = it.get("value") or []

#         # value를 리스트로 정규화
#         values = value if isinstance(value, list) else [value]

#         # value가 비어있으면 한 칸은 만들되 값은 공백
#         if not values:
#             values = [""]

#         for v in values:
#             # 1행: 로직명
#             ws.cell(row=1, column=col, value="문항 스킵")
#             # 2행: start,end
#             ws.cell(row=2, column=col, value=f"{start},{end}".strip(","))
#             # 3행: 선택번호 (숫자면 int로)
#             if isinstance(v, int):
#                 ws.cell(row=3, column=col, value=v)
#             else:
#                 s = str(v).strip()
#                 ws.cell(row=3, column=col, value=int(s) if s.isdigit() else s)

#             col += 1

#     for c in range(1, col):
#         ws.column_dimensions[get_column_letter(c)].width = 18

#     wb.save(exell_path)



