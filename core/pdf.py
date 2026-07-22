"""PDF 텍스트 추출 (pypdf)."""
from pypdf import PdfReader


def extract_text(pdf_file) -> str | None:
    """업로드된 PDF에서 텍스트를 추출한다.

    반환값이 None이면 호출부에서 사용자에게 원인(암호화/스캔본 등)을 안내해야 한다.
    스캔(이미지)형 PDF는 텍스트가 없어 빈 결과가 나온다.
    나이스(NEIS) 발급본 등 빈 비밀번호로 열리는 암호화 PDF는 자동으로 해제를 시도한다.
    """
    if pdf_file is None:
        return None
    try:
        reader = PdfReader(pdf_file)
        if reader.is_encrypted:
            if not reader.decrypt(""):
                return None
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return None
    text = text.strip()
    return text or None
