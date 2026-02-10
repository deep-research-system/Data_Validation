from pathlib import Path
from pdf2image import convert_from_path
import pytesseract


# 레이아웃형태도 불안정하고 글자도 제대로 인식못함 


# tesseract, poppler 따로 다운해야함
# ===== 환경에 맞게 경로만 수정 =====
TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_BIN = r"C:\poppler\Library\bin"
# =================================


def ocr_pdf_korean(
    pdf_path: str | Path,
    out_txt: str | Path,
    dpi: int = 600,
) -> Path:
    pdf_path = Path(pdf_path)
    out_txt = Path(out_txt)

    # tesseract 경로 지정 (Windows 필수)
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

    # 1) PDF → 이미지
    images = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        poppler_path=POPPLER_BIN,
        fmt="png",
    )

    # 2) OCR
    texts: list[str] = []
    for i, img in enumerate(images, start=1):
        text = pytesseract.image_to_string(
            img,
            lang="kor+eng",
            config="--oem 3 --psm 4 -c preserve_interword_spaces=1",
        )
        texts.append(f"\n\n===== PAGE {i} =====\n{text.strip()}")

    # 3) 저장
    out_txt.write_text("\n".join(texts), encoding="utf-8")
    return out_txt


if __name__ == "__main__":
    result = ocr_pdf_korean(
        pdf_path="data/(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.pdf",
        out_txt="data/pdf_ocr(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.txt",
    )
    print("OCR 완료:", result)
