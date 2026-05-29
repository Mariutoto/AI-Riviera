import html
import json
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests


BASE_URL = "https://www.la-tour-de-peilz.ch/"
LIST_URL = "https://www.la-tour-de-peilz.ch/politique/ordre-du-jour.php"
START_DATE = date(2025, 2, 5)
TODAY = date.today()
HEADERS = {"User-Agent": "AI-Riviera agenda importer"}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = PROJECT_ROOT / "documents" / "la-tour-de-peilz"
SESSIONS_ROOT = PROJECT_ROOT / "data" / "sessions" / "la-tour-de-peilz"

MONTHS = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}


class TextAndLinksParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[dict] = []
        self.current_href: str | None = None
        self.current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "a":
            self.current_href = attrs_dict.get("href")
            self.current_text = []
        if tag in {"br", "p", "li", "div", "h1", "h2", "h3", "h4"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.current_href:
            text = clean_spaces("".join(self.current_text))
            self.links.append({"href": self.current_href, "text": text})
            self.current_href = None
            self.current_text = []
        if tag in {"p", "li", "div", "h1", "h2", "h3", "h4"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self.current_href:
            self.current_text.append(data)


def clean_spaces(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_text(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def parse_french_date(label: str) -> date | None:
    match = re.search(r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(20\d{2})", label.lower())
    if not match:
        return None
    day = int(match.group(1))
    month = MONTHS[match.group(2)]
    year = int(match.group(3))
    return date(year, month, day)


def collect_session_pages() -> list[dict]:
    page_html = fetch_text(LIST_URL)
    sessions = []
    seen = set()
    for match in re.finditer(
        r"""href=["'](apercu_ordre-du-jour\.php\?id=\d+)["'][\s\S]{0,300}?Séance du\s+([^<]+)""",
        page_html,
        flags=re.I,
    ):
        detail_url = urljoin(LIST_URL, html.unescape(match.group(1)))
        if detail_url in seen:
            continue
        seen.add(detail_url)

        label = clean_spaces(f"Séance du {re.sub(r'<[^>]+>', ' ', match.group(2))}")
        session_date = parse_french_date(label)
        if not session_date:
            continue
        if START_DATE <= session_date <= TODAY:
            sessions.append({"source_url": detail_url, "label": label, "session_date": session_date})

    return sorted(sessions, key=lambda item: item["session_date"], reverse=True)


def normalize_pdf_url(page_url: str, href: str) -> str | None:
    full_url = urljoin(page_url, html.unescape(href))
    if "viewer.php" in full_url and "file=" in full_url:
        file_value = parse_qs(urlparse(full_url).query).get("file", [""])[0]
        full_url = urljoin(BASE_URL, unquote(file_value))
    if ".pdf" not in full_url.lower():
        return None
    return full_url


def extract_main_text(full_text: str) -> str:
    start = full_text.find("COMMUNE DE LA-TOUR-DE-PEILZ")
    end = full_text.find("Législature 2021-2026", start)
    if start == -1:
        start = full_text.find("Ordre du jour")
    if end == -1:
        end = len(full_text)
    return clean_spaces(full_text[start:end])


def parse_agenda_items(main_text: str) -> list[dict]:
    compact = re.sub(r"\s+", " ", main_text)
    pattern = re.compile(r"(?<!\d)(\d+(?:\.\d+)*)\.\s+")
    matches = list(pattern.finditer(compact))
    items = []
    for index, match in enumerate(matches):
        number = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(compact)
        title = compact[start:end].strip(" -")
        if title:
            items.append({"number": number, "title": title})
    return items


def parse_session(session: dict) -> dict:
    source_url = session["source_url"]
    page_html = fetch_text(source_url)
    parser = TextAndLinksParser()
    parser.feed(page_html)

    full_text = clean_spaces("".join(parser.text_parts))
    main_text = extract_main_text(full_text)
    linked_documents = []
    seen_pdf_urls = set()
    for link in parser.links:
        pdf_url = normalize_pdf_url(source_url, link["href"])
        if not pdf_url or pdf_url in seen_pdf_urls:
            continue
        seen_pdf_urls.add(pdf_url)
        linked_documents.append(
            {
                "title": link["text"],
                "pdf_url": pdf_url,
                "filename": Path(unquote(urlparse(pdf_url).path)).name,
            }
        )

    session_date = session["session_date"]
    time_match = re.search(r"à\s+(\d{1,2}:\d{2})", main_text)
    place_match = re.search(r"\d{4}\s+à\s+\d{1,2}:\d{2}\s+(.+?)\n\s*Ordre du jour", main_text, re.S)
    place = clean_spaces(place_match.group(1)) if place_match else ""

    return {
        "commune": "La Tour-de-Peilz",
        "type": "ordre_du_jour",
        "session_date": session_date.isoformat(),
        "label": session["label"],
        "time": time_match.group(1) if time_match else "",
        "place": place,
        "source_url": source_url,
        "agenda_items": parse_agenda_items(main_text),
        "linked_documents": linked_documents,
        "text": main_text,
    }


def write_session_files(session_data: dict) -> None:
    year = session_data["session_date"][:4]
    slug = session_data["session_date"]

    session_dir = SESSIONS_ROOT / year
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / f"{slug}.json").write_text(
        json.dumps(session_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    document_dir = DOCUMENTS_ROOT / year / "ordres-du-jour"
    document_dir.mkdir(parents=True, exist_ok=True)
    text_path = document_dir / f"{slug}-ordre-du-jour.txt"
    json_path = document_dir / f"{slug}-ordre-du-jour.json"
    text_path.write_text(session_data["text"], encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "commune": session_data["commune"],
                "year": year,
                "category": "ordres-du-jour",
                "filename": text_path.name,
                "source_page": session_data["source_url"],
                "session_date": session_data["session_date"],
                "time": session_data["time"],
                "place": session_data["place"],
                "linked_documents_count": len(session_data["linked_documents"]),
                "text_path": str(text_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    sessions = collect_session_pages()
    results = []
    for session in sessions:
        session_data = parse_session(session)
        write_session_files(session_data)
        results.append(
            {
                "session_date": session_data["session_date"],
                "source_url": session_data["source_url"],
                "agenda_items_count": len(session_data["agenda_items"]),
                "linked_documents_count": len(session_data["linked_documents"]),
            }
        )
        print(
            f"{session_data['session_date']} - "
            f"{len(session_data['agenda_items'])} agenda items, "
            f"{len(session_data['linked_documents'])} linked PDFs"
        )

    manifest = {
        "commune": "La Tour-de-Peilz",
        "start_date": START_DATE.isoformat(),
        "end_date": TODAY.isoformat(),
        "excluded_future_sessions": True,
        "sessions_count": len(results),
        "sessions": results,
    }
    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = SESSIONS_ROOT / "manifest_ordres_du_jour_2025_2026.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
