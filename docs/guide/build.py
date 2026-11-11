#!/usr/bin/env python3
"""Builds docs/prompt-vault-study-guide.pdf from guide/chapters/*.md.

    uv run --with markdown --with pygments --with playwright --with pypdf python docs/guide/build.py

Needs Chrome or Chromium (set CHROME_PATH if it is not found automatically).
Code listings are copied from the real source files (the `@code` directive), so the guide
cannot drift silently: the build fails if a cited file or line range does not exist.

Chapter source format (Markdown plus a few directives):

    ::: chapter 4 "Title" "Subtitle"        first line of every chapter file
    ## 4.1 Section title                     becomes a TOC entry
    ::: concept|analogy|project|warning|lesson|checkpoint|summary|question [Title]
    ...markdown...
    :::
    @code core/src/domain/status.py:1-20 "optional title"
    @figure layers "Caption text"            figures are defined in figures.py
    ```bash title="Terminal"                 fenced blocks with an optional title
"""
from __future__ import annotations

import html
import os
import pathlib
import re
import sys

import markdown
from playwright.sync_api import sync_playwright
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, get_lexer_for_filename
from pypdf import PdfReader

import figures

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # prompt-vault/
OUT = HERE.parent / "prompt-vault-study-guide.pdf"
TITLE = "Prompt Vault, from the inside"
SUBTITLE = "Python, hexagonal architecture, NATS, FastAPI and React explained with a real project"

BOX_LABELS = {
    "concept": "CONCEPT",
    "analogy": "ANALOGY",
    "project": "IN THE PROJECT",
    "warning": "WATCH OUT",
    "lesson": "LESSON LEARNED",
    "checkpoint": "CHECKPOINT",
    "summary": "CHAPTER SUMMARY",
    "question": "GUIDING QUESTION",
}

FORMATTER = HtmlFormatter(nowrap=True, classprefix="t-")


def md(text: str) -> str:
    return markdown.markdown(text, extensions=["tables", "sane_lists"], output_format="html5")


def lexer_for(name: str, lang: str | None):
    try:
        return get_lexer_by_name(lang) if lang else get_lexer_for_filename(name)
    except Exception:
        return TextLexer()


def code_block(source: str, lang: str | None, title: str, filename: str = "") -> str:
    body = highlight(source.rstrip("\n"), lexer_for(filename, lang), FORMATTER)
    return f'<div class="code"><div class="code-title">{html.escape(title)}</div><pre>{body}</pre></div>'


def include_code(spec: str, title: str | None) -> str:
    m = re.match(r"(?P<path>[^:\s]+)(?::(?P<a>\d+)-(?P<b>\d+))?$", spec)
    if not m:
        raise SystemExit(f"bad @code spec: {spec}")
    path = ROOT / m["path"]
    if not path.is_file():
        raise SystemExit(f"@code: file not found: {m['path']}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if m["a"]:
        a, b = int(m["a"]), int(m["b"])
        if not (1 <= a <= b <= len(lines)):
            raise SystemExit(f"@code: range {a}-{b} outside {m['path']} ({len(lines)} lines)")
        lines = lines[a - 1 : b]
    # remove the common indentation so excerpts read well
    indent = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    text = "\n".join(l[indent:] for l in lines)
    label = title or m["path"]
    return code_block(text, None, label, m["path"])


def render_chapter(path: pathlib.Path):
    """Return (chapter_id, title, html, headings) for one chapter file."""
    raw = path.read_text(encoding="utf-8").splitlines()
    head = re.match(r'::: chapter (\S+) "(.*?)" "(.*?)"$', raw[0])
    if not head:
        raise SystemExit(f"{path.name}: first line must be '::: chapter N \"Title\" \"Subtitle\"'")
    cid, title, subtitle = head.groups()
    is_appendix = cid.isalpha()
    out: list[str] = []
    buf: list[str] = []
    headings: list[tuple[str, str]] = []
    counter = 0

    def flush():
        nonlocal counter
        if not buf:
            return
        rendered = md("\n".join(buf))
        def add_id(m):
            nonlocal counter
            counter += 1
            hid = f"s-{cid}-{counter}"
            headings.append((hid, re.sub(r"<[^>]+>", "", m.group(1))))
            return f'<h2 id="{hid}">{m.group(1)}</h2>'
        out.append(re.sub(r"<h2>(.*?)</h2>", add_id, rendered))
        buf.clear()

    i = 1
    while i < len(raw):
        line = raw[i]
        if line.startswith("```"):
            flush()
            info = line[3:].strip()
            lang = info.split()[0] if info else None
            tm = re.search(r'title="(.*?)"', info)
            i += 1
            block = []
            while not raw[i].startswith("```"):
                block.append(raw[i])
                i += 1
            out.append(code_block("\n".join(block), lang, tm.group(1) if tm else (lang or "")))
        elif line.startswith("@code "):
            flush()
            m = re.match(r'@code (\S+)(?: "(.*?)")?$', line)
            out.append(include_code(m[1], m[2]))
        elif line.startswith("@figure "):
            flush()
            m = re.match(r'@figure (\S+) "(.*?)"$', line)
            out.append(figures.figure(m[1], m[2]))
        elif line.startswith("::: "):
            flush()
            m = re.match(r"::: (\w+)(?: (.*))?$", line)
            kind, btitle = m[1], (m[2] or "")
            i += 1
            inner = []
            while raw[i].strip() != ":::":
                inner.append(raw[i])
                i += 1
            label = BOX_LABELS[kind] + (f" · {btitle}" if btitle else "")
            out.append(f'<div class="box {kind}"><div class="box-title">{html.escape(label)}</div>{md(chr(10).join(inner))}</div>')
        else:
            buf.append(line)
        i += 1
    flush()
    marker = f"{'APPENDIX' if is_appendix else 'CHAPTER'} {cid}"
    num = cid if is_appendix else cid
    chapter = (
        f'<section class="chapter" id="ch-{cid}">'
        f'<header class="chapter-head"><div class="num">{num}</div><div>'
        f'<div class="marker">{marker}</div><h1>{html.escape(title)}</h1><p class="sub">{html.escape(subtitle)}</p></div></header>'
        + "".join(out)
        + "</section>"
    )
    return cid, title, chapter, headings


def build_html(chapters, pages: dict[str, str]) -> str:
    figures.reset()
    toc = []
    for cid, title, _, headings in chapters:
        label = f"{cid}. " if not cid.isalpha() else f"{cid}. "
        toc.append(
            f'<a class="toc1" href="#ch-{cid}"><span>{label}{html.escape(title)}</span><i></i><b>{pages.get("ch-" + cid, "")}</b></a>'
        )
        for hid, text in headings:
            toc.append(f'<a class="toc2" href="#{hid}"><span>{html.escape(text)}</span><i></i><b>{pages.get(hid, "")}</b></a>')
    css = (HERE / "guide.css").read_text(encoding="utf-8") + FORMATTER.get_style_defs(".code pre")
    cover = (
        f'<section class="cover"><div class="cover-in"><p class="kicker">STUDY GUIDE</p><div class="cover-title">{TITLE}</div>'
        f'<p class="cover-sub">{SUBTITLE}</p>{figures.figure("cover", "")}'
        f'<p class="cover-foot">Study material generated from the implemented and tested code of the three projects: core, api and front.</p></div></section>'
    )
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{TITLE}</title><style>{css}</style></head><body>'
        f"{cover}<section class=\"toc\" id=\"toc\"><h1>Contents</h1><p class=\"toc-hint\">Click any entry to jump to its page.</p>{''.join(toc)}</section>"
        + "".join(c[2] for c in chapters)
        + "</body></html>"
    )


def chrome_path() -> str:
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    for pattern in (".cache/ms-playwright/chromium-*/chrome-linux*/chrome",):
        found = sorted(pathlib.Path.home().glob(pattern))
        if found:
            return str(found[-1])
    for name in ("google-chrome", "chromium", "chromium-browser"):
        from shutil import which
        if which(name):
            return which(name)
    raise SystemExit("Chrome/Chromium not found. Set CHROME_PATH.")


def render(html_text: str, dest: pathlib.Path, chrome_decor: bool = True) -> None:
    tmp = HERE / ".build.html"
    tmp.write_text(html_text, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome_path(), args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(tmp.as_uri())
        page.wait_for_timeout(300)
        page.pdf(
            path=str(dest),
            prefer_css_page_size=True,
            display_header_footer=chrome_decor,
            header_template=(
                "<div style=\"font:8px 'DejaVu Sans',sans-serif;color:#667;width:100%;padding:0 18mm;display:flex;justify-content:space-between\">"
                "<span>PROMPT VAULT · STUDY GUIDE</span><span>Python · hexagonal architecture · NATS · FastAPI · React</span></div>"
            ),
            footer_template=(
                "<div style=\"font:8px 'DejaVu Sans',sans-serif;color:#667;width:100%;text-align:center\"><span class='pageNumber'></span></div>"
            ),
            print_background=True,
            outline=True,
            tagged=True,
        )
        browser.close()
    tmp.unlink(missing_ok=True)


def locate_pages(pdf: pathlib.Path, chapters) -> dict[str, str]:
    reader = PdfReader(str(pdf))
    texts = [re.sub(r"\s+", "", (pg.extract_text() or "")) for pg in reader.pages]
    pages: dict[str, str] = {}
    cursor = 0
    for cid, _, _, headings in chapters:
        marker = f"{'APPENDIX' if cid.isalpha() else 'CHAPTER'}{cid}"
        for idx in range(cursor, len(texts)):
            if marker in texts[idx]:
                cursor = idx
                pages[f"ch-{cid}"] = str(idx + 1)
                break
        for hid, text in headings:
            needle = re.sub(r"\s+", "", text)
            for idx in range(cursor, len(texts)):
                if needle in texts[idx]:
                    cursor = idx
                    pages[hid] = str(idx + 1)
                    break
    return pages


def with_clean_cover(pdf: pathlib.Path, cover_html: str) -> None:
    """Page 1 is re-rendered without the running header/footer and swapped in."""
    from pypdf import PdfWriter

    cover_pdf = HERE / ".cover.pdf"
    render(cover_html, cover_pdf, chrome_decor=False)
    writer = PdfWriter(clone_from=str(pdf))
    writer.insert_page(PdfReader(str(cover_pdf)).pages[0], 0)
    writer.remove_page(1)
    with open(pdf, "wb") as handle:
        writer.write(handle)
    cover_pdf.unlink(missing_ok=True)


def main() -> None:
    chapters = [render_chapter(p) for p in sorted((HERE / "chapters").glob("*.md"))]
    work = HERE / ".pass1.pdf"
    render(build_html(chapters, {}), work)
    pages = locate_pages(work, chapters)
    final_html = build_html(chapters, pages)
    render(final_html, OUT)
    cover_only = re.sub(r'<section class="toc".*</body>', "</body>", final_html, flags=re.S)
    with_clean_cover(OUT, cover_only)
    work.unlink(missing_ok=True)
    total = len(PdfReader(str(OUT)).pages)
    missing = [c[0] for c in chapters if f"ch-{c[0]}" not in pages]
    print(f"wrote {OUT.relative_to(ROOT)}: {total} pages, {len(chapters)} chapters" + (f" (pages not found for: {missing})" if missing else ""))


if __name__ == "__main__":
    sys.exit(main())
