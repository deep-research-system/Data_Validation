import win32com.client
from pathlib import Path


def convert_hwp_to_pdf(hwp_path: str | Path, pdf_path: str | Path):
    hwp_path = Path(hwp_path).resolve()
    pdf_path = Path(pdf_path).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    hwp = win32com.client.gencache.EnsureDispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")

    # 1) 파일 열기
    hwp.HAction.GetDefault("FileOpen", hwp.HParameterSet.HFileOpen.HSet)
    hwp.HParameterSet.HFileOpen.OpenFileName = str(hwp_path)  
    # 필요하면 포맷 명시 (대부분 자동 인식)
    # hwp.HParameterSet.HFileOpen.OpenFormat = "HWP"
    hwp.HAction.Execute("FileOpen", hwp.HParameterSet.HFileOpen.HSet)

    # 2) PDF로 저장
    hwp.HAction.GetDefault("FileSaveAs", hwp.HParameterSet.HFileOpen.HSet)
    hwp.HParameterSet.HFileOpen.SaveFileName = str(pdf_path)  
    hwp.HParameterSet.HFileOpen.SaveFormat = "PDF" 
    hwp.HAction.Execute("FileSaveAs", hwp.HParameterSet.HFileOpen.HSet)

    hwp.Quit()
    return pdf_path


if __name__ == "__main__":
    pdf_path = convert_hwp_to_pdf(
        hwp_path="data/test.hwp",
        pdf_path="data/testtesteasdfasdf.pdf",
    )
    
    print(f"변환 완료: {pdf_path}")
