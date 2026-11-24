"""web-search: DuckDuckGo Lite で検索し、上位5件を返す（標準ライブラリのみ）。

使い方: 検索クエリを標準入力で渡す。
出力: 番号付きで「タイトル / URL / 要約1行」。結果なし・失敗時も文章で返す。
"""
import html
import re
import sys
import urllib.parse
import urllib.request

ENDPOINT = "https://lite.duckduckgo.com/lite/?q="
MAX_RESULTS = 5
TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def search(query: str):
    url = ENDPOINT + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read().decode("utf-8", errors="replace")
    links = []
    for m in re.finditer(
        r"href=\"//duckduckgo\.com/l/\?uddg=([^&\"]+)[^\"]*\"[^>]*>(.*?)</a>",
        body, re.S,
    ):
        links.append((clean(m.group(2)), urllib.parse.unquote(m.group(1))))
    snippets = [clean(s) for s in re.findall(
        r"class=['\"]result-snippet['\"][^>]*>(.*?)</td>", body, re.S)]
    results = []
    for i, (title, link) in enumerate(links[:MAX_RESULTS]):
        snippet = snippets[i] if i < len(snippets) else ""
        results.append((title, link, snippet))
    return results


def main() -> int:
    query = sys.stdin.read().strip()
    if not query:
        print("クエリが空です。検索したい問いを標準入力で渡してください。")
        return 1
    try:
        results = search(query)
    except Exception as e:  # ネットワーク・応答形式の変化など
        print(f"検索に失敗しました: {type(e).__name__}: {e}")
        return 1
    if not results:
        print(f"「{query}」の検索結果は見つかりませんでした。")
        return 0
    lines = [f"検索クエリ: {query}", f"上位{len(results)}件:"]
    for i, (title, link, snippet) in enumerate(results, 1):
        lines.append(f"{i}. {title}")
        lines.append(f"   {link}")
        if snippet:
            lines.append(f"   {snippet[:120]}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
