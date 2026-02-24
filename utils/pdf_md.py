# from pathlib import Path
# from docling.document_converter import DocumentConverter

# INPUT_PDF = Path("data/계약의사_하.pdf")
# OUT_MD = Path("output/계약의사_하.md")

# converter = DocumentConverter()

# result = converter.convert(INPUT_PDF)

# md_text = result.document.export_to_markdown()

# OUT_MD.write_text(md_text, encoding="utf-8")

# print("완료:", OUT_MD)
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

INPUT_PDF = Path("data/계약의사_하.pdf")
OUT_MD = Path("output/계약의사_하.no_ocr.md")

pdf_opts = PdfPipelineOptions()

pdf_opts.do_ocr = False              # ✅ OCR 완전 끔
pdf_opts.do_table_structure = True   # 표 구조는 유지 (원하면 False 가능)

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pdf_opts
        )
    }
)

result = converter.convert(INPUT_PDF)
md_text = result.document.export_to_markdown()

OUT_MD.write_text(md_text, encoding="utf-8")

print("완료:", OUT_MD)


from pathlib import Path
import re

IN_MD = Path("output/계약의사_하.no_ocr.md")
OUT_MD = Path("output/계약의사_하.cleaned.md")

def clean_md(text: str) -> str:
    # 1) 연속된 '※' 덩어리는 제거/축약 (빈칸처럼 쓰인 경우가 대부분)
    text = re.sub(r"(?:\s*※\s*){2,}", " ", text)

    # 2) 한글/영문/숫자 사이에 낀 '※'는 공백으로 (문장 흐름 복원)
    text = re.sub(r"(?<=[0-9A-Za-z가-힣])\s*※\s*(?=[0-9A-Za-z가-힣])", " ", text)

    # 3) 문장부호 주변의 쓸모없는 '※' 제거
    text = re.sub(r"\s*※\s*(?=[\.\,\?\!\:\;\)\]])", "", text)
    text = re.sub(r"(?<=[\(\[\-])\s*※\s*", "", text)

    # 4) 공백 정리
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5) 보기 라인(①②③...)에서 숫자/동그라미 앞뒤 잡음 제거 보강
    text = re.sub(r"-\s*([①②③④⑤⑥⑦⑧⑨⑩])\s*", r"- \1 ", text)

    return text.strip() + "\n"

md = IN_MD.read_text(encoding="utf-8", errors="ignore")
OUT_MD.write_text(clean_md(md), encoding="utf-8")

print("완료:", OUT_MD)