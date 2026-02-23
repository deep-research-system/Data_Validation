from pathlib import Path
from docling.document_converter import DocumentConverter

INPUT_PDF = Path("data/클라우드컴퓨팅_하.pdf")
OUT_MD = Path("output/클라우드컴퓨팅_하.md")

converter = DocumentConverter()

result = converter.convert(INPUT_PDF)

md_text = result.document.export_to_markdown()

OUT_MD.write_text(md_text, encoding="utf-8")

print("완료:", OUT_MD)