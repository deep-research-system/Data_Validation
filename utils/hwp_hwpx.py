# utils/hwp_hwpx.py
import win32com.client
from pathlib import Path


def convert_hwp_to_hwpx(hwp_path: str | Path, hwpx_path: str | Path) -> Path:
    hwp_path = Path(hwp_path).resolve()
    hwpx_path = Path(hwpx_path).resolve()
    hwpx_path.parent.mkdir(parents=True, exist_ok=True)

    hwp = win32com.client.gencache.EnsureDispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")

    # 파일 열기
    hwp.HAction.GetDefault("FileOpen", hwp.HParameterSet.HFileOpen.HSet)
    hwp.HParameterSet.HFileOpen.OpenFileName = str(hwp_path)
    hwp.HAction.Execute("FileOpen", hwp.HParameterSet.HFileOpen.HSet)

    # HWPX로 저장
    hwp.HAction.GetDefault("FileSaveAs", hwp.HParameterSet.HFileOpen.HSet)
    hwp.HParameterSet.HFileOpen.SaveFileName = str(hwpx_path)
    hwp.HParameterSet.HFileOpen.SaveFormat = "HWPX"
    hwp.HAction.Execute("FileSaveAs", hwp.HParameterSet.HFileOpen.HSet)

    hwp.Quit()
    return hwpx_path


if __name__ == "__main__":
    out = convert_hwp_to_hwpx(
        "data/(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.hwp",
        "data/hwpx(STI)_(설문지)_부산연구원_2025년 부산 청년패널조사_250623_상.hwpx",
    )
    print(f"변환 완료: {out}")
