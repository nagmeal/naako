"""wiki-ingest: プロジェクトルートの wiki_ingest.py を実行する薄いラッパー。"""
import subprocess
import sys
from pathlib import Path

TIMEOUT = 1100  # SKILL.md の timeout: 1200 より少し短く


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    script = root / "wiki_ingest.py"
    if not script.is_file():
        print("wiki_ingest.py がプロジェクトルートにありません。")
        return 1
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=TIMEOUT, cwd=root,
        )
    except subprocess.TimeoutExpired:
        print(f"取り込みが {TIMEOUT} 秒で終わりませんでした。")
        return 1
    out = (proc.stdout or "").strip()
    if out:
        print(out)
    if proc.returncode != 0:
        tail = (proc.stderr or "")[-500:]
        if tail:
            print(f"[stderr] {tail}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
