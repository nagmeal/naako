"""wiki_ingest: docs-inbox/ の資料をプロジェクト wiki に取り込む。

使い方: python wiki_ingest.py
  docs-inbox/ 直下のファイルを走査し、対応形式はテキスト抽出（決定的処理）
  → LLM で要約 → wiki/pages/<slug>.md を生成し、wiki/index.md を再生成する。
  処理済みファイルは docs-inbox/done/ へ移動する。
  読めない物（対象外形式・抽出が空・破損）は無理に読まず、取り込みを中止して
  ファイルは inbox に残し、最後にアラートとして報告する。

対応形式: .xlsx / .pptx / .txt / .md / .csv（PDFは対象外）
依存: Python 標準ライブラリのみ（LLM 呼び出しは requests 経由で Ollama API）
"""
import html
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INBOX = ROOT / "docs-inbox"
DONE = INBOX / "done"
WIKI = ROOT / "wiki"
PAGES = WIKI / "pages"

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
LLM_TIMEOUT = 120
MAX_FILES_PER_RUN = 10
LLM_INPUT_CHARS = 6000
PAGE_TEXT_CHARS = 8000
SUPPORTED = {".xlsx", ".pptx", ".txt", ".md", ".csv"}


# ---------------------------------------------------------------- 抽出
def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _xml_texts(xml: str, tag: str) -> list[str]:
    return [html.unescape(t) for t in re.findall(rf"<{tag}[^>]*>([^<]*)</{tag}>", xml)]


def extract_xlsx(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            xml = z.read("xl/sharedStrings.xml").decode("utf-8", errors="replace")
            shared = [html.unescape("".join(re.findall(r"<t[^>]*>([^<]*)</t>", si)))
                      for si in re.findall(r"<si>(.*?)</si>", xml, re.S)]
        sheet_names: list[str] = []
        if "xl/workbook.xml" in names:
            wb = z.read("xl/workbook.xml").decode("utf-8", errors="replace")
            sheet_names = re.findall(r"<sheet[^>]*name=\"([^\"]+)\"", wb)
        sheet_files = sorted(
            (n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
        out: list[str] = []
        for i, sf in enumerate(sheet_files):
            title = sheet_names[i] if i < len(sheet_names) else Path(sf).stem
            xml = z.read(sf).decode("utf-8", errors="replace")
            out.append(f"## シート: {title}")
            rows = re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S)
            for row in rows[:200]:
                cells: list[str] = []
                for cm in re.finditer(r"<c\b([^>]*)>(.*?)</c>", row, re.S):
                    attrs, inner = cm.group(1), cm.group(2)
                    tm = re.search(r't="(\w+)"', attrs)
                    ctype = tm.group(1) if tm else ""
                    v = re.search(r"<v>([^<]*)</v>", inner)
                    if ctype == "s" and v:
                        idx = int(v.group(1))
                        cells.append(shared[idx] if idx < len(shared) else "")
                    elif v:
                        cells.append(html.unescape(v.group(1)))
                    else:
                        t = re.search(r"<t[^>]*>([^<]*)</t>", inner)
                        cells.append(html.unescape(t.group(1)) if t else "")
                line = " | ".join(cells).rstrip(" |")
                if line.strip():
                    out.append(line)
            out.append("")
        return "\n".join(out)


def extract_pptx(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        slide_files = sorted(
            (n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
        out: list[str] = []
        for i, sf in enumerate(slide_files, 1):
            xml = z.read(sf).decode("utf-8", errors="replace")
            out.append(f"## スライド {i}")
            for para in re.findall(r"<a:p>(.*?)</a:p>", xml, re.S):
                line = "".join(_xml_texts(para, "a:t")).strip()
                if line:
                    out.append(line)
            out.append("")
        return "\n".join(out)


def extract(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".xlsx":
        return extract_xlsx(path)
    if ext == ".pptx":
        return extract_pptx(path)
    return read_text_file(path)


# ---------------------------------------------------------------- 要約
def summarize(text: str, fallback_title: str) -> tuple[str, str, list[str]]:
    """LLM でタイトル・要約・要点を作る。失敗時は決定的フォールバック。"""
    prompt = f"""次の文書を wiki ページ用に整理してください。出力は必ず次の形式だけにしてください。
タイトル: （文書のタイトルを1行で）
要約: （3行以内の要約）
要点:
- （要点を最大5つ、箇条書き）

文書:
{text[:LLM_INPUT_CHARS]}"""
    try:
        import requests
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content":
                 "あなたは文書の整理係です。求められた形式を厳密に守り、"
                 "前置きや挨拶は書かないでください。結果に無い推測はしないでください。"},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }, timeout=LLM_TIMEOUT)
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")
    except Exception:
        content = ""
    title, summary, points = fallback_title, "", []
    if content:
        m = re.search(r"タイトル:\s*(.+)", content)
        if m:
            title = m.group(1).strip()
        m = re.search(r"要約:\s*(.+?)(?=\n要点:|\Z)", content, re.S)
        if m:
            summary = m.group(1).strip()
        m = re.search(r"要点:\s*(.+)\Z", content, re.S)
        if m:
            points = [ln.strip()[2:].strip() for ln in m.group(1).splitlines()
                      if ln.strip().startswith("- ")]
    if not summary:
        # フォールバック: 先頭の非空行を要約代わりにする
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        summary = " ".join(lines[:3])[:200]
    return title, summary, points[:5]


# ---------------------------------------------------------------- ページ
def slugify(stem: str) -> str:
    slug = re.sub(r'[\\/:*?"<>|]', "_", stem).strip()
    return slug or "untitled"


def write_page(slug: str, title: str, source: str, summary: str,
               points: list[str], text: str) -> Path:
    PAGES.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = PAGES / f"{slug}.md"
    existed = page.exists()
    body_text = text[:PAGE_TEXT_CHARS]
    truncated = "\n\n（抽出テキストは上限で切り捨て）" if len(text) > PAGE_TEXT_CHARS else ""
    points_md = "\n".join(f"- {p}" for p in points) if points else "（なし）"
    page.write_text(f"""---
title: {title}
source: {source}
ingested: {now}
---

# {title}

## 要約
{summary}

## 要点
{points_md}

## 抽出テキスト
{body_text}{truncated}
""", encoding="utf-8")
    return page


def rebuild_index() -> None:
    WIKI.mkdir(parents=True, exist_ok=True)
    lines = ["# プロジェクト Wiki", ""]
    pages = sorted(PAGES.glob("*.md")) if PAGES.exists() else []
    if not pages:
        lines.append("（まだページがありません）")
    for p in pages:
        head = p.read_text(encoding="utf-8", errors="replace")[:1000]
        title = re.search(r"^title:\s*(.+)$", head, re.M)
        source = re.search(r"^source:\s*(.+)$", head, re.M)
        date = re.search(r"^ingested:\s*(.+)$", head, re.M)
        t = title.group(1) if title else p.stem
        s = source.group(1) if source else "?"
        d = date.group(1) if date else "?"
        lines.append(f"- [{t}](pages/{p.name})（出典: {s} / 取り込み: {d}）")
    (WIKI / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 本体
def main() -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    DONE.mkdir(parents=True, exist_ok=True)
    files = sorted(f for f in INBOX.iterdir()
                   if f.is_file() and f.name != ".gitkeep")
    done_list: list[str] = []
    alerts: list[str] = []
    for f in files[:MAX_FILES_PER_RUN]:
        ext = f.suffix.lower()
        if ext not in SUPPORTED:
            alerts.append(f"{f.name}: 対象外の形式です")
            continue
        try:
            text = extract(f)
        except Exception as e:
            alerts.append(f"{f.name}: 抽出に失敗しました（{type(e).__name__}）")
            continue
        if not text.strip():
            alerts.append(f"{f.name}: 抽出テキストが空でした")
            continue
        title, summary, points = summarize(text, f.stem)
        slug = slugify(f.stem)
        page = write_page(slug, title, f.name, summary, points, text)
        shutil.move(str(f), str(DONE / f.name))
        done_list.append(f"{page.relative_to(ROOT)}（元: {f.name}）")
    if len(files) > MAX_FILES_PER_RUN:
        alerts.append(f"ほか {len(files) - MAX_FILES_PER_RUN} 件は次回に回しました"
                      f"（1回の上限 {MAX_FILES_PER_RUN} 件）")
    rebuild_index()
    print(f"取り込み完了: {len(done_list)}件")
    for d in done_list:
        print(f"- ページ作成: {d}")
    if alerts:
        print(f"アラート: {len(alerts)}件")
        for a in alerts:
            print(f"- {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
