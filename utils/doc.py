# 실행 40~50초, 글자 잘 나옴, 표 같은 레이아웃 지킴

from pathlib import Path
from docling.document_converter import DocumentConverter


# 입력 PDF
source = "data/(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.pdf"

# 출력 디렉터리
out_dir = Path("ouput")

# 출력 파일명 (PDF 이름 그대로 .md)
out_md = out_dir / (Path(source).stem + ".md")

# 변환
converter = DocumentConverter()
result = converter.convert(source)

# markdown 추출
markdown_text = result.document.export_to_markdown()

# 파일 저장 (UTF-8)
out_md.write_text(markdown_text, encoding="utf-8")

print(f"Markdown 저장 완료: {out_md}")