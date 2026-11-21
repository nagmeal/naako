"""Agent Skills 互換の最小ローダー（Python 標準ライブラリのみ）

スキル = フォルダ1個 + SKILL.md。
SKILL.md 先頭の YAML フロントマターに name / description を書き、
本文に手順、scripts/ に実行スクリプトを置く（Agent Skills 標準仕様の作法）。

段階的開示:
  1. 普段は catalog_text() の「名前＋説明」だけをプロンプトに入れる（軽い）
  2. 使うスキルが決まったら load_body() で本文を入れる
  3. scripts/run.py があれば run_script() で決定的に実行できる

使い方:
    loader = SkillLoader("skills")
    print(loader.catalog_text())
    body = loader.load_body("plan-lint")
    rc, out = loader.run_script("plan-lint", plan_text)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_SCRIPT_OUTPUT = 4000


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """SKILL.md 先頭の --- ブロックから key: value を拾う（簡易パーサ）。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, text[m.end():]


class Skill:
    def __init__(self, directory: Path, meta: dict, body: str):
        self.dir = directory
        self.name = meta.get("name", directory.name)
        self.description = meta.get("description", "")
        # スクリプトへ渡す入力の種類: "task"（既定）= タスク本文 / "plan" = 計画テキスト
        self.input = meta.get("input", "task")
        self.body = body.strip()

    @property
    def script(self) -> Path | None:
        p = self.dir / "scripts" / "run.py"
        return p.resolve() if p.is_file() else None

    def __repr__(self) -> str:  # デバッグ用
        return f"Skill({self.name!r})"


class SkillLoader:
    def __init__(self, skills_dir: str | Path = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: dict[str, Skill] = {}
        self.warnings: list[str] = []
        self.scan()

    def scan(self) -> None:
        self.skills.clear()
        self.warnings.clear()
        if not self.skills_dir.is_dir():
            return
        for d in sorted(self.skills_dir.iterdir()):
            md = d / "SKILL.md"
            if not d.is_dir() or not md.is_file():
                continue
            meta, body = _parse_frontmatter(md.read_text(encoding="utf-8"))
            skill = Skill(d, meta, body)
            if skill.name != d.name:
                self.warnings.append(
                    f"{d.name}: name '{skill.name}' がフォルダ名と一致しません")
                continue
            if not NAME_RE.match(skill.name):
                self.warnings.append(f"{d.name}: name の形式が不正です")
                continue
            if not skill.description:
                self.warnings.append(f"{d.name}: description が空です")
                continue
            if skill.input not in ("task", "plan"):
                self.warnings.append(
                    f"{d.name}: input '{skill.input}' が不正なので task として扱います")
                skill.input = "task"
            self.skills[skill.name] = skill

    def catalog_text(self) -> str:
        """段階1: 名前＋説明だけの一覧（プロンプトに常時入れる用）。"""
        return "\n".join(
            f"- {s.name}: {s.description}" for s in self.skills.values())

    def get(self, name: str) -> Skill | None:
        return self.skills.get(name)

    def load_body(self, name: str) -> str:
        """段階2: SKILL.md 本文（手順）を返す。なければ空文字。"""
        s = self.skills.get(name)
        return s.body if s else ""

    def run_script(self, name: str, input_text: str,
                   timeout: int = 60) -> tuple[int, str]:
        """段階3: scripts/run.py を標準入力つきで実行する。

        実行はスキルのフォルダを作業ディレクトリにして閉じる。
        戻り値: (終了コード, 標準出力＋標準エラー末尾)
        """
        s = self.skills.get(name)
        if s is None:
            return -1, f"skill not found: {name}"
        if s.script is None:
            return -1, f"skill has no scripts/run.py: {name}"
        try:
            proc = subprocess.run(
                [sys.executable, str(s.script)],
                input=input_text, capture_output=True, text=True,
                timeout=timeout, cwd=s.dir,
            )
        except subprocess.TimeoutExpired:
            return -1, f"script timeout ({timeout}s): {name}"
        out = proc.stdout or ""
        if proc.stderr:
            out += "\n[stderr]\n" + proc.stderr[-1000:]
        return proc.returncode, out[:MAX_SCRIPT_OUTPUT]


if __name__ == "__main__":  # 単体確認用: python skills.py [skills_dir]
    loader = SkillLoader(sys.argv[1] if len(sys.argv) > 1 else "skills")
    print("== catalog ==")
    print(loader.catalog_text() or "(スキルなし)")
    for w in loader.warnings:
        print("warning:", w)
