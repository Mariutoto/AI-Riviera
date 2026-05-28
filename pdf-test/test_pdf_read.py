from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests


VIEWER_URL = (
    "https://www.la-tour-de-peilz.ch/tools/pdf-viewer/web/viewer.php?"
    "file=https://www.la-tour-de-peilz.ch/doc_uploads/images/politique/"
    "conseil-communal/motions-postulats/2026/"
    "Postulat-Huber-Chervet-Quai-roussy.pdf"
)


def extract_pdf_url(viewer_url: str) -> str:
    query = parse_qs(urlparse(viewer_url).query)
    return unquote(query["file"][0])


def extract_text(pdf_path: Path) -> str:
    import fitz

    document = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in document)


def main() -> None:
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_url = extract_pdf_url(VIEWER_URL)
    pdf_path = output_dir / "Postulat-Huber-Chervet-Quai-roussy.pdf"
    text_path = output_dir / "Postulat-Huber-Chervet-Quai-roussy.txt"

    response = requests.get(
        pdf_url,
        headers={"User-Agent": "AI-Riviera PDF test"},
        timeout=30,
    )
    response.raise_for_status()
    pdf_path.write_bytes(response.content)

    text = extract_text(pdf_path)
    text_path.write_text(text, encoding="utf-8")

    print(f"PDF saved to: {pdf_path}")
    print(f"Text saved to: {text_path}")
    print(f"Extracted characters: {len(text)}")
    print()
    print(text[:1200].strip())


if __name__ == "__main__":
    main()
