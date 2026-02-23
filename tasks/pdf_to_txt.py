import pdfplumber
from pathlib import Path

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
        pdf_path="data/가족보호자_임종기돌봄 설문지(최종)_심층인터뷰 추가_중.pdf",
        out_txt="output_txt/가족보호자_임종기돌봄 설문지(최종)_심층인터뷰 추가_중.txt"
    )

    print(f"텍스트 추출 완료: {txt_path}")