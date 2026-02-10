import os
from pyhwpx import Hwp



def hwp_to_txt(hwp_path: str, out_txt: str):
    """
    한/글(.hwp) 파일을 텍스트(.txt) 파일로 변환합니다.
    
    :param hwp_path: 원본.hwp 파일 경로
    :param out_txt: 최종 uft8-텍스트 파일
    """
    # 경로 정규화
    # 상대경로에 보안경고/오동작이 많음
    hwp_path = os.path.abspath(hwp_path)
    out_txt = os.path.abspath(out_txt)

    # 한글이 항상 CP949(ANSI)로 저장하므로 중간파일 필요
    tmp_txt = out_txt + ".ansi.txt"
    
    # 한글 실행
    hwp = Hwp()

    # 한글 파일 열기
    try:
        hwp.open(hwp_path, arg="suspendpassword:false;forceopen:true;versionwarning:false")

        hwp.SaveAs(tmp_txt, "TEXT")  # 보통 CP949(ANSI)로 저장됨

    finally:
        try:
            hwp.quit()
        except Exception:
            pass

    # CP949로 읽어서 UTF-8로 변환 저장
    with open(tmp_txt, "r", encoding="cp949", errors="replace") as f:
        text = f.read()

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)

    os.remove(tmp_txt)


# 사용 예시
hwp_to_txt("data/test_hwp.hwp", "data/hwp_text.txt")
