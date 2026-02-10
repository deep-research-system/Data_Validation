import win32com.client as win32
import os

def hwp_to_txt_utf8(hwp_path: str, out_txt_utf8: str):
    hwp_path = os.path.abspath(hwp_path)
    out_txt_utf8 = os.path.abspath(out_txt_utf8)

    tmp_txt = out_txt_utf8 + ".ansi.txt"

    hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
    try:
        hwp.Open(hwp_path)
        hwp.SaveAs(tmp_txt, "TEXT")  # 보통 CP949(ANSI)로 저장됨
    finally:
        try:
            hwp.Quit()
        except Exception:
            pass

    # CP949로 읽어서 UTF-8로 변환 저장
    with open(tmp_txt, "r", encoding="cp949", errors="replace") as f:
        text = f.read()

    with open(out_txt_utf8, "w", encoding="utf-8") as f:
        f.write(text)

    os.remove(tmp_txt)


# 사용 예시
hwp_to_txt_utf8("data/test_hwp.hwp", "data/output.txt")
