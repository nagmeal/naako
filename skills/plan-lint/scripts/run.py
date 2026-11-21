#!/usr/bin/env python3
"""plan-lint: 計画テキストの書式チェック（標準入力 → 行ごとの判定）。

形式: 番号. [タスク名] 内容 (タイプ: nlp/code) [(スキル: name)]
NG が1行でもあれば終了コード 1。
"""
import re
import sys

TASK_RE = re.compile(
    r"^\d+\.\s+\[(.+?)\]\s+(.+?)\s+\(タイプ:\s*(nlp|code)\)"
    r"(?:\s*\(スキル:\s*([a-z0-9-]+)\))?\s*$")


MAX_DESC_CHARS = 40
MULTI_STEP_HINTS = ("して、", "し、", "その後", "ついでに")


def granularity_warnings(desc: str) -> list[str]:
    """粒度チェック: 小さいモデルで実行するには大きすぎるタスクを警告する。"""
    warns = []
    if len(desc) > MAX_DESC_CHARS:
        warns.append(f"説明が長い（{len(desc)}字）")
    if any(h in desc for h in MULTI_STEP_HINTS):
        warns.append("複数の手順が1タスクに入っている疑い")
    return warns


def main() -> int:
    text = sys.stdin.read()
    ok = ng = warn_total = 0
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        # 判定対象は「番号.」で始まるタスク行の候補だけ。
        # 前置きや説明文の行は対象外（parse_plan も読み飛ばすため）。
        if not re.match(r"^\d+\.", stripped):
            continue
        m = TASK_RE.match(stripped)
        if m:
            ok += 1
            skill = f" skill={m.group(4)}" if m.group(4) else ""
            print(f"L{i}: OK [{m.group(1)}] type={m.group(3)}{skill}")
            for w in granularity_warnings(m.group(2)):
                warn_total += 1
                print(f"L{i}: WARN 粒度: {w}")
        else:
            ng += 1
            print(f"L{i}: NG 形式が合いません: {line.strip()[:60]}")
    print(f"summary: ok={ok} ng={ng} warn={warn_total}")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
