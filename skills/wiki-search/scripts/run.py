"""wiki-search: wiki/pages/ をキーワード検索する（決定的処理のみ）。

入力（タスク文）からキーワードと文字 bigram を作り、ページ本文の
出現回数でスコア付けして上位3件の要約・要点を返す。
"""
import re
import sys
from pathlib import Path

MAX_PAGES = 3
SECTION_CHARS = 1200


def keywords(query: str) -> tuple[list[str], set[str]]:
    toks = re.split(r"[\s、。，．・:：/／「」（）()]+", query)
    words = [t for t in toks if len(t) >= 2]
    grams: set[str] = set()
    for t in toks:
        s = re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龥]", "", t)
        for i in range(len(s) - 1):
            grams.add(s[i:i + 2])
    return words, grams


def section(text: str, name: str) -> str:
    m = re.search(rf"## {name}\n(.*?)(?=\n## |\Z)", text, re.S)
    return m.group(1).strip() if m else ""


def main() -> int:
    query = sys.stdin.read().strip()
    if not query:
        print("検索したい内容が空です。")
        return 1
    root = Path(__file__).resolve().parents[3]
    pages_dir = root / "wiki" / "pages"
    pages = sorted(pages_dir.glob("*.md")) if pages_dir.exists() else []
    if not pages:
        print("wiki にページがまだありません。")
        return 0
    words, grams = keywords(query)
    scored: list[tuple[int, Path, str]] = []
    for p in pages:
        text = p.read_text(encoding="utf-8", errors="replace")
        title_m = re.search(r"^title:\s*(.+)$", text, re.M)
        title = title_m.group(1) if title_m else p.stem
        score = 0
        for w in words:
            score += title.count(w) * 5 + text.count(w) * 2
        for g in grams:
            score += text.count(g)
        if score > 0:
            scored.append((score, p, text))
    if not scored:
        print("該当するページは見つかりませんでした。")
        return 0
    scored.sort(key=lambda x: -x[0])
    print(f"検索: {query}（{len(scored)}件ヒット、上位{MAX_PAGES}件）")
    for score, p, text in scored[:MAX_PAGES]:
        title_m = re.search(r"^title:\s*(.+)$", text, re.M)
        source_m = re.search(r"^source:\s*(.+)$", text, re.M)
        title = title_m.group(1) if title_m else p.stem
        source = source_m.group(1) if source_m else "?"
        summary = section(text, "要約")
        points = section(text, "要点")
        print(f"\n■ {title}（出典: {source}）")
        if summary:
            print(f"要約: {summary[:SECTION_CHARS]}")
        if points:
            print(f"要点:\n{points[:SECTION_CHARS]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
