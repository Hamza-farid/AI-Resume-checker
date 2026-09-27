"""
📄 Turns an uploaded resume into Markdown text.

PDF  -> up to 3 PyMuPDF4LLM methods, tried in order:
          1. classic       : finds columns, keeps tables       (normal / 2-column / table resumes)
          2. ignore boxes  : classic + ignores drawings         (Canva / shaded-box resumes)
          3. layout        : never drops text, may mix columns  (last backup)
        The first method that keeps >= 97% of the PDF's words wins.
        "Answer key" = page.get_text() -> every word in the PDF, no formatting.

DOCX -> Word -> HTML (mammoth) -> unwrap invisible layout tables -> Markdown (MarkItDown)

The Markdown text is exactly what the AI will read later.
"""

import io
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import mammoth
import pymupdf
import pymupdf4llm
from bs4 import BeautifulSoup
from markitdown import MarkItDown, StreamInfo  # needs: pip install "markitdown[docx]"
from pymupdf4llm.helpers import pymupdf_rag

import config
from logger import get_logger

log = get_logger(__name__)

MIN_TEXT_COVERAGE = 97.0  # % of the original words a method must keep to be accepted

# Markdown table divider line, e.g. |---|---|
_TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", re.MULTILINE)
# Leftover image tags, e.g. ![](image.png)
_IMAGE_TAG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
# Underline tags from the PDF, e.g. **<u>SKILLS</u>** -> **SKILLS**
_UNDERLINE_TAG = re.compile(r"</?u>", re.IGNORECASE)
_WORD = re.compile(r"\w+", re.UNICODE)


class ResumeParseError(Exception):
    """A problem we can explain to the user in plain words."""


@dataclass
class ParsedResume:
    original_name: str
    file_type: str        # "pdf" or "docx"
    markdown: str
    pages: int | None     # Word files don't have fixed pages
    words: int
    tables: int
    method: str           # which reading method was used
    text_coverage: float  # % of the file's words found in our Markdown (100 = nothing lost)


# ─────────────────────────── helpers ───────────────────────────

def _clean(markdown: str) -> str:
    text = _IMAGE_TAG.sub("", markdown)
    text = _UNDERLINE_TAG.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)  # no huge empty gaps
    return text.strip()


def _coverage(markdown: str, answer_key: str) -> float:
    """% of the answer-key words that also appear in the Markdown (counts repeats too)."""
    key = Counter(w.lower() for w in _WORD.findall(answer_key))
    if not key:
        return 0.0
    found = Counter(w.lower() for w in _WORD.findall(markdown))
    return 100 * sum((key & found).values()) / sum(key.values())


# ─────────────────────────── PDF ───────────────────────────

# (name shown in logs, function that turns a PDF document into Markdown)
_PDF_METHODS = [
    ("Method 1 (classic)",
     lambda doc: pymupdf_rag.to_markdown(doc, write_images=False, show_progress=False)),
    ("Method 2 (ignore boxes)",
     lambda doc: pymupdf_rag.to_markdown(doc, write_images=False, ignore_graphics=True, show_progress=False)),
    ("Method 3 (layout)",
     lambda doc: pymupdf4llm.to_markdown(doc, write_images=False, use_ocr=False, show_progress=False)),
]


def _open_pdf(data: bytes) -> pymupdf.Document:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        raise ResumeParseError("This PDF could not be opened. It may be damaged.") from e
    if doc.needs_pass:
        doc.close()
        raise ResumeParseError("This PDF is password protected. Please upload an unlocked copy.")
    return doc


def _pdf_to_markdown(filename: str, data: bytes) -> tuple[str, int, str, float]:
    doc = _open_pdf(data)
    try:
        pages = doc.page_count
        answer_key = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()

    if len(answer_key.strip()) < config.MIN_TEXT_CHARS:
        raise ResumeParseError(
            "This PDF has almost no text. It is probably a scanned image. Please upload a text-based PDF."
        )

    best = None  # (coverage, name, markdown)
    for name, method in _PDF_METHODS:
        doc = _open_pdf(data)  # fresh copy for each method
        try:
            markdown = _clean(method(doc))
        except Exception as e:
            log.warning(f"🔧 {name} crashed on '{filename}': {e}")
            continue
        finally:
            doc.close()

        cov = _coverage(markdown, answer_key)
        log.info(f"🔍 '{filename}' | {name} | {cov:.0f}% text kept")

        if best is None or cov > best[0]:
            best = (cov, name, markdown)
        if cov >= MIN_TEXT_COVERAGE:
            return markdown, pages, name, cov

    if best is None:
        raise ResumeParseError("This PDF could not be read by any method. Check the logs for details.")

    cov, name, markdown = best
    log.warning(f"⚠️ '{filename}' | no method kept {MIN_TEXT_COVERAGE:.0f}% | using {name} ({cov:.0f}%) | please check it")
    return markdown, pages, name, cov


# ─────────────────────────── DOCX ───────────────────────────

_BLOCK_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table"]


def _is_layout_table(table) -> bool:
    """A table used to build columns (cells full of headings/bullets), not a real data table."""
    for cell in table.find_all(["td", "th"]):
        if len(cell.find_all(_BLOCK_TAGS, recursive=False)) >= 3 or len(cell.get_text(" ", strip=True)) > 200:
            return True
    return False


def _unwrap_layout_tables(html: str) -> tuple[str, int]:
    """Replace layout tables with their content: left column fully, then the next column."""
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):  # images are ignored completely
        img.decompose()

    unwrapped = 0
    for table in soup.find_all("table"):  # outer tables come first
        if table.parent is None or not _is_layout_table(table):
            continue
        rows = [row.find_all(["td", "th"], recursive=False) for row in table.find_all("tr") if row.find_parent("table") is table]
        n_cols = max((len(r) for r in rows), default=0)

        box = soup.new_tag("div")
        for col in range(n_cols):
            for row in rows:
                if col < len(row):
                    for child in list(row[col].contents):
                        box.append(child.extract())
        table.replace_with(box)
        unwrapped += 1
    return str(soup), unwrapped


def _docx_to_markdown(filename: str, data: bytes) -> tuple[str, str, float]:
    try:
        html = mammoth.convert_to_html(io.BytesIO(data)).value
        answer_key = mammoth.extract_raw_text(io.BytesIO(data)).value
    except Exception as e:
        log.warning(f"📝 Could not read '{filename}': {e}")
        raise ResumeParseError("This Word file could not be opened. It may be damaged or not a real .docx.") from e

    html, unwrapped = _unwrap_layout_tables(html)
    if unwrapped:
        log.info(f"🧱 '{filename}' | unwrapped {unwrapped} layout table(s) into normal text")

    result = MarkItDown().convert_stream(io.BytesIO(html.encode("utf-8")), stream_info=StreamInfo(extension=".html"))
    markdown = _clean(result.markdown)
    cov = _coverage(markdown, answer_key)
    method = "MarkItDown + unwrap layout tables" if unwrapped else "MarkItDown"
    return markdown, method, cov


# ─────────────────────────── main entry ───────────────────────────

def parse_resume(filename: str, data: bytes) -> ParsedResume:
    """File name + file bytes -> ParsedResume (or ResumeParseError)."""
    size_mb = len(data) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        raise ResumeParseError(f"File is {size_mb:.1f} MB. The limit is {config.MAX_UPLOAD_MB} MB.")

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in config.ALLOWED_EXTENSIONS:
        raise ResumeParseError("Only PDF and DOCX files are supported.")

    log.info(f"📥 Parsing '{filename}' ({size_mb:.2f} MB, {ext.upper()})")

    if ext == "pdf":
        markdown, pages, method, cov = _pdf_to_markdown(filename, data)
    else:
        markdown, method, cov = _docx_to_markdown(filename, data)
        pages = None

    if len(markdown) < config.MIN_TEXT_CHARS:
        raise ResumeParseError("This file has almost no readable text.")

    parsed = ParsedResume(
        original_name=filename,
        file_type=ext,
        markdown=markdown,
        pages=pages,
        words=len(markdown.split()),
        tables=len(_TABLE_DIVIDER.findall(markdown)),
        method=method,
        text_coverage=round(cov, 1),
    )
    badge = "✅" if cov >= MIN_TEXT_COVERAGE else "⚠️"
    log.info(
        f"{badge} '{filename}' | {method} | {cov:.0f}% text kept | "
        f"pages={pages or '-'} | words={parsed.words} | tables={parsed.tables}"
    )
    return parsed
