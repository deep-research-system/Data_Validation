import pdfplumber
from pathlib import Path
import win32com.client

# 텍스트 추출은 제일잘하나 표 글자가 뒤죽박죽으로 나옴
# 빠름

def extract_text_from_pdf(pdf_path: str | Path, out_txt: str | Path):
    pdf_path = Path(pdf_path)
    out_txt = Path(out_txt)

    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            texts.append(f"\n\n===== PAGE {i} =====\n{text}")

    out_txt.write_text("\n".join(texts), encoding="utf-8")
    return out_txt


if __name__ == "__main__":
    txt_path = extract_text_from_pdf(
        pdf_path="data/(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.pdf",
        out_txt="output/pdf_text(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.txt"
    )

    print(f"텍스트 추출 완료: {txt_path}")