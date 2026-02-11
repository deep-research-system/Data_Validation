# xml을 이용한 hwpx -> markdown 변환
# 텍스트만 가져와서 표형식에 취약한거같음
# XML에서 xpl에서 빈칸은 데이터키없으면 md에 반영 하지못함



from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional


def _tag_ends(elem: ET.Element, name: str) -> bool:
    # 네임스페이스 포함 태그 대응: "{ns}tbl" -> "tbl" 비교
    return elem.tag.endswith("}" + name) or elem.tag.endswith(":" + name) or elem.tag.endswith(name)


def _collect_text(node: ET.Element) -> str:
    """
    node 아래의 텍스트(<...:t>)를 순서대로 모아 하나의 문자열로 만든다.
    표 셀(tc) 단위 텍스트 수집에 사용.
    """
    parts: List[str] = []
    for e in node.iter():
        if _tag_ends(e, "t") and e.text:
            txt = e.text.strip()
            if txt:
                parts.append(txt)
    # 셀 내부는 보통 단어 단위로 쪼개질 수 있어서 공백으로 합침
    return " ".join(parts).strip()


def _table_to_markdown(tbl: ET.Element) -> str:
    """
    <tbl> -> Markdown table 문자열.
    첫 행을 헤더로 가정(설문지 표에서도 보통 첫 줄이 컬럼 느낌이거나, 아니면 그냥 헤더처럼 둬도 무방)
    """
    rows: List[List[str]] = []

    for tr in tbl.iter():
        if not _tag_ends(tr, "tr"):
            continue

        row: List[str] = []
        for tc in list(tr):
            # tc가 바로 child가 아닐 수도 있어서 iter로 탐색
            if _tag_ends(tc, "tc"):
                cell_text = _collect_text(tc)
                row.append(cell_text)
            else:
                # tr의 직계 child가 tc가 아니면, 그 안에서 tc를 찾는다
                for inner_tc in tc.iter():
                    if _tag_ends(inner_tc, "tc"):
                        row.append(_collect_text(inner_tc))

        # 빈 행 제외
        if any(c.strip() for c in row):
            rows.append(row)

    if not rows:
        return ""

    # 행마다 컬럼 수가 다르면 최대 컬럼 수에 맞춰 패딩
    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]

    # Markdown table 생성
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []

    md = []
    md.append("| " + " | ".join(header) + " |")
    md.append("| " + " | ".join(["---"] * max_cols) + " |")
    for r in body:
        md.append("| " + " | ".join(r) + " |")

    return "\n".join(md)


def extract_section0_xml(hwpx_path: Path) -> str:
    with zipfile.ZipFile(hwpx_path, "r") as z:
        with z.open("Contents/section0.xml") as f:
            return f.read().decode("utf-8", errors="replace")


def hwpx_to_markdown(hwpx_path: str | Path) -> str:
    hwpx_path = Path(hwpx_path).resolve()
    xml_text = extract_section0_xml(hwpx_path)

    root = ET.fromstring(xml_text)

    out_lines: List[str] = []

    # 1) 표를 발견하면 표를 MD로 변환해서 넣는다.
    # 2) 표 밖 텍스트는 문단 단위로 수집(일단 단순)
    #    (정교화는 다음 단계: 문단(p) 단위, 문항 번호 기준 헤딩 처리 등)

    for node in root.iter():
        if _tag_ends(node, "tbl"):
            md_tbl = _table_to_markdown(node)
            if md_tbl:
                out_lines.append(md_tbl)
                out_lines.append("")  # 빈 줄
            continue

    # 표만 먼저 확인하고 싶으면 아래 텍스트 수집은 잠시 주석 처리해도 됨
    # out_lines.append("\n\n".join(_collect_text(p) for p in root.iter() if _tag_ends(p, "p")))

    return "\n".join(out_lines).strip()


def save_md(hwpx_path: str | Path, md_path: str | Path) -> Path:
    md = hwpx_to_markdown(hwpx_path)
    md_path = Path(md_path).resolve()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    return md_path


if __name__ == "__main__":
    out = save_md("output/hwpx(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.hwpx", "data/test_table_only.md")
    print(f"생성 완료: {out}")
