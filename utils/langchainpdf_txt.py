# 텍스트 출력이 잘되고 빠름 그러나 pdf라서 표형식이 있는 부분에서 순서가 뒤죽박죽



from langchain_community.document_loaders import PyPDFLoader
import asyncio
from pathlib import Path




async def main():
    loader = PyPDFLoader("data/(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.pdf", extraction_mode="plain")
    docs = await loader.aload()
    
    full_text = "\n".join([doc.page_content for doc in docs])
    
    out_path = Path("data/output.txt")
    out_path.write_text(full_text, encoding="utf-8")
    
    print(f"저장완료: {out_path}")
    
    


if __name__ == "__main__":
    asyncio.run(main())