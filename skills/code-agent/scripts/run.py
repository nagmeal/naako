"""code-agent: Claude Code にファイル編集を伴う作業を委譲する（標準ライブラリのみ）。

使い方: 委譲したい作業の指示を標準入力で渡す。
実行: プロジェクトルート（skills/ の親）を作業場所に、receiver.py と同じ
      呼び出し方（Ollama 経由・gemma4:cloud・ターン/予算上限つき）で
      `claude -p` を1回起動し、完了まで任せる。コミットはしない。
出力: エージェントの結果テキスト＋ターン数とコストの要約行。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

MODEL = "gemma4:cloud"
OLLAMA_BASE_URL = "http://localhost:11434"
MAX_TURNS = 20
MAX_BUDGET_USD = "2"
ALLOWED_TOOLS = "Read,Edit,Write,Glob,Grep,Bash"
SUBPROCESS_TIMEOUT = 840  # SKILL.md の timeout: 900 より少し短く


def project_root() -> Path:
    # scripts/run.py → code-agent → skills → プロジェクトルート
    return Path(__file__).resolve().parents[3]


def main() -> int:
    task = sys.stdin.read().strip()
    if not task:
        print("指示が空です。委譲したい作業を標準入力で渡してください。")
        return 1
    env = dict(os.environ)
    # 素の claude は Anthropic 未ログインのため、Ollama 経由に固定する
    env["ANTHROPIC_BASE_URL"] = OLLAMA_BASE_URL
    env["ANTHROPIC_AUTH_TOKEN"] = "ollama"
    env["ANTHROPIC_API_KEY"] = ""
    cmd = [
        "claude", "-p", task,
        "--model", MODEL,
        "--output-format", "json",
        "--allowedTools", ALLOWED_TOOLS,
        "--max-turns", str(MAX_TURNS),
        "--max-budget-usd", MAX_BUDGET_USD,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=SUBPROCESS_TIMEOUT, cwd=project_root(), env=env,
        )
    except subprocess.TimeoutExpired:
        print(f"コーディングエージェントが {SUBPROCESS_TIMEOUT} 秒で終わりませんでした。")
        return 1
    except FileNotFoundError:
        print("claude コマンドが見つかりません。Claude Code のインストールが必要です。")
        return 1
    raw = (proc.stdout or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("エージェントの出力を解釈できませんでした。末尾:")
        print(raw[-1000:] or (proc.stderr or "")[-1000:])
        return 1
    result = (data.get("result") or "").strip()
    turns = data.get("num_turns", "?")
    cost = data.get("total_cost_usd", "?")
    if data.get("is_error"):
        print(f"エージェントがエラーを返しました: {result}")
        return 1
    print(result)
    print(f"\n[code-agent] turns={turns} cost_usd={cost}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
