import win32com.client
from pathlib import Path

def convert_hwp_to_docx(hwp_path: str | Path, docx_path: str | Path) -> Path:
    hwp_path = Path(hwp_path).resolve()
    docx_path = Path(docx_path).resolve()
    docx_path.parent.mkdir(parents=True, exist_ok=True)

    hwp = win32com.client.gencache.EnsureDispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")

    # open
    hwp.HAction.GetDefault("FileOpen", hwp.HParameterSet.HFileOpen.HSet)
    hwp.HParameterSet.HFileOpen.OpenFileName = str(hwp_path)
    hwp.HAction.Execute("FileOpen", hwp.HParameterSet.HFileOpen.HSet)

    # save as (포맷 지정 X)
    hwp.HAction.GetDefault("FileSaveAs", hwp.HParameterSet.HFileSaveAs.HSet)
    hwp.HParameterSet.HFileSaveAs.SaveFileName = str(docx_path)
    hwp.HAction.Execute("FileSaveAs", hwp.HParameterSet.HFileSaveAs.HSet)

    hwp.Quit()
    return docx_path

if __name__ == "__main__":
    convert_hwp_to_docx("data/test_hwp.hwp", "data/test_hwp.docx")
