import json

import settings
from llm_client import LLMClient
from workspace_manager import WorkspaceManager
from typing import List, Optional

POINT_MAX_CHARS = 100  # 要点1つの最大文字数
POINTS_MAX = 10        # 保持する要点の最大件数


# なあこ（単一エージェント版）
# 計画・実行・要約を一人で担う。PDCAの多段構成は廃止し、
# 必要になったら「スキル」として外付けする方針。
class NaakoAgent:
    def __init__(self, llm_client: LLMClient, workspace: WorkspaceManager, skills=None):
        self.llm = llm_client
        self.ws = workspace
        self.skills = skills
        self.name = settings.AGENT_SETTINGS["main"]["name"]
        # 結果台帳: 段階どうしの受け渡しはモデルの文章ではなく、
        # 検証可能な結果（スクリプト出力・終了コード）で行う。
        self.ledger: List[dict] = []
        # 要点リスト: 作業中の「頭」に残すのは圧縮した要点だけ。
        # 詳細は台帳（results.json）に置き、要点だけが段階間を受け継ぐ。
        self.points: List[str] = []
        self.goal: str = ""

    def plan(self, user_request: str, strict: bool = False,
             reset: bool = True) -> str:
        # 依頼を最小タスクに分解し、plan.txt に保存して返す。
        prompt = f"""
ユーザーの依頼を分析し、最小単位のタスクに分解して計画を立ててください。
各タスクは一度に実行できる最小限の範囲にしてください。

タスクの粒度のルール（小さいモデルでも実行できるように）:
- 1タスクには動詞を1つだけ入れること（「〜して、〜する」は2つのタスクに分ける）
- 1タスクの成果物は1つだけにすること（出力の形が一言で言える粒度にする）
- タスクの説明は40字以内で書くこと
- 前のタスクの結果が必要な場合は、その内容をタスクの説明に含めること

依頼: {user_request}

出力形式（この形式の行だけを出力すること）:
1. [タスク名] 内容 (タイプ: nlp/code)
2. [タスク名] 内容 (タイプ: nlp/code)
"""
        if strict:
            prompt += """
注意: 挨拶や前置き、説明文は一切書かないでください。
番号付きのタスク行だけを出力してください。各行は必ず [タスク名] で始めてください。
"""
        if self.skills and self.skills.catalog_text():
            prompt += f"""
利用可能なスキル（役立つタスクには行末に (スキル: スキル名) を付けること）:
{self.skills.catalog_text()}
"""
        plan = self.llm.generate("main", prompt)
        self.ws.write("plan.txt", plan)
        if reset:
            # 実行の開始で台帳と要点をリセットする（段階の区切り）。
            # 最終チェック後の再計画（reset=False）では引き継ぐ。
            self.goal = user_request
            self.ledger = []
            self._save_ledger()
            self.points = []
            self._save_points()
        return plan

    def _save_ledger(self) -> None:
        self.ws.write("results.json",
                      json.dumps(self.ledger, ensure_ascii=False, indent=1))

    def _save_points(self) -> None:
        self.ws.write("points.json",
                      json.dumps(self.points, ensure_ascii=False, indent=1))

    def _points_context(self) -> str:
        """実行ステップへ渡す文脈。要点だけを渡し、詳細は台帳に置く。"""
        lines = [f"目標: {self.goal}"]
        if self.points:
            lines.append("これまでの要点:")
            lines += [f"- {p}" for p in self.points]
        else:
            lines.append("これまでの要点: （まだありません）")
        return "\n".join(lines)

    def compress_point(self, entry: dict) -> str:
        """タスク結果を要点1つ（100字以内）に圧縮する専用呼び出し。

        「やる」と「要点に残す」を分けるための独立したワンショット。
        失敗したら決定的フォールバック（出力の先頭行を100字で切る）。
        """
        output = (entry.get("output") or "").strip()
        fallback = ""
        for line in output.splitlines():
            if line.strip():
                fallback = line.strip().lstrip("# ").strip()
                break
        if entry.get("status") == "error" and not fallback:
            fallback = f"{entry.get('name', 'タスク')}: エラーで終了"
        fallback = fallback[:POINT_MAX_CHARS]
        if not output:
            return fallback or f"{entry.get('name', 'タスク')}: 結果なし"
        prompt = f"""次のタスク結果を、要点1つに圧縮してください。
条件: {POINT_MAX_CHARS}字以内、1行、事実だけを書くこと。
前置き・説明・「要点:」などの見出しは付けないこと。

タスク: {entry.get('name', '')}
結果:
{output[:1200]}"""
        try:
            text = self.llm.generate("main", prompt)
        except Exception:
            text = ""
        for line in (text or "").splitlines():
            line = line.strip().lstrip("- ").strip()
            if line.startswith("要点:") or line.startswith("要点："):
                line = line[3:].strip()
            if line and not line.startswith("Error calling"):
                return line[:POINT_MAX_CHARS]
        return fallback

    def _prioritize_points(self) -> None:
        """要点が上限を超えたら、目標に照らして大事なものだけ残す。"""
        numbered = "\n".join(
            f"{i}. {p}" for i, p in enumerate(self.points, 1))
        prompt = f"""目標: {self.goal}

現在の要点リスト:
{numbered}

要点が多すぎます。目標に対して「今一番大事なもの」だけを最大{POINTS_MAX}件選び、
選んだ要点をそのままの文で、1行に1つずつ出力してください。
新しい文を作らないでください。"""
        try:
            text = self.llm.generate("main", prompt)
        except Exception:
            text = ""
        kept = []
        for line in (text or "").splitlines():
            line = line.strip().lstrip("- ").strip()
            line = line.split(". ", 1)[-1] if ". " in line[:5] else line
            if line in self.points and line not in kept:
                kept.append(line)
        if kept:
            self.points = kept[:POINTS_MAX]
        else:
            # 選べなかったら新しいものを残す（決定的フォールバック）
            self.points = self.points[-POINTS_MAX:]

    def check_goal(self, results: Optional[List[dict]] = None) -> tuple:
        """最終チェック: 最初の目標を達成したかを要点と成否で照合する。

        戻り値: (達成したか, 不足の説明)。読み取れなければ達成扱いにし、
        無限にやり直さない。
        """
        entries = results if results is not None else self.ledger
        statuses = "\n".join(
            f"- [{e['name']}] status={e['status']}" for e in entries)
        points = "\n".join(f"- {p}" for p in self.points) or "（要点なし）"
        prompt = f"""依頼（目標）: {self.goal}

これまでの要点:
{points}

タスクの成否:
{statuses}

この目標は達成できましたか。次の形式だけで答えてください。
達成: はい、または いいえ
不足: （未達の場合だけ、何が足りないかを1行で）"""
        try:
            text = self.llm.generate("main", prompt)
        except Exception:
            return True, ""
        import re
        m = re.search(r"達成[:：]\s*(はい|いいえ)", text or "")
        if not m or m.group(1) == "はい":
            return True, ""
        m2 = re.search(r"不足[:：]\s*(.+)", text or "")
        return False, (m2.group(1).strip() if m2 else "目標の一部が未達")

    def execute(self, task_description: str, task_type: str,
                skill_name: Optional[str] = None,
                task_name: str = "") -> dict:
        # タスクを1件実行し、結果を台帳に記録して返す。
        # スクリプトを持つスキルでは、台帳の「出力」はスクリプトの生出力
        # （検証可能な事実）とし、モデルの文章は「補足」に分ける。
        if (skill_name and self.skills
                and skill_name in getattr(self.skills, "excluded", set())):
            # 封印スキル（APIモードの code-agent 等）は実行せず台帳に残す
            entry = {
                "name": task_name or task_description,
                "skill": skill_name,
                "status": "error",
                "output": f"スキル '{skill_name}' はこのモードでは封印されています。",
                "note": "",
            }
            entry["point"] = entry["output"][:POINT_MAX_CHARS]
            self.points.append(entry["point"])
            self._save_points()
            self.ledger.append(entry)
            self._save_ledger()
            self.ws.append("memo.txt",
                           f"[{task_description}] 封印スキルのため未実行: {skill_name}")
            return entry
        skill_block = ""
        script_result = None
        if skill_name and self.skills:
            body = self.skills.load_body(skill_name)
            if body:
                skill_block += f"\n\n【スキル手順: {skill_name}】\n{body}"
            skill = self.skills.get(skill_name)
            if skill and skill.script:
                # スクリプトへの入力は SKILL.md の input 宣言で切り替える
                # （task = タスク本文 / plan = 計画テキスト plan.txt）
                input_text = task_description
                if getattr(skill, "input", "task") == "plan":
                    input_text = self.ws.read("plan.txt") or task_description
                script_result = self.skills.run_script(skill_name, input_text)
                rc, out = script_result
                skill_block += f"\n\n【スクリプト実行結果 (終了コード {rc})】\n{out}"

        prompt = f"""
以下のタスクを実行してください。
要点は参考情報です。要点が無くても、タスク文だけで実行してください。{skill_block}

タスク: {task_description}
{self._points_context()}
"""
        note = self.llm.generate("main", prompt)

        if script_result is not None:
            rc, out = script_result
            entry = {
                "name": task_name or task_description,
                "skill": skill_name,
                "status": "ok" if rc == 0 else "error",
                "output": out.strip(),
                "note": note.strip(),
            }
        else:
            entry = {
                "name": task_name or task_description,
                "skill": skill_name,
                "status": "ok",
                "output": note.strip(),
                "note": "",
            }
        # 要点は圧縮専用の呼び出しで作り、台帳と要点リストの両方に残す
        entry["point"] = self.compress_point(entry)
        self.points.append(entry["point"])
        if len(self.points) > POINTS_MAX:
            self._prioritize_points()
        self._save_points()
        self.ledger.append(entry)
        self._save_ledger()
        self._append_draft(entry)
        self.ws.append("memo.txt",
                       f"[{task_description}] 完了: {entry['output'][:50]}...")
        return entry

    def _append_draft(self, entry: dict) -> None:
        """成果物の下書きに、この段階の書き足しを追記する。

        最終成果物は「最後に一気に生成するもの」ではなく、各段階が
        少しずつ書き足してきた蓄積として作る（下書きはディスクに置く
        ので、1回の生成量に縛られず大きくできる）。
        """
        if entry.get("status") == "error":
            body = "（このタスクはエラーで終了しました）"
        else:
            body = (entry.get("output") or "").strip()[:4000]
        if not body:
            return
        self.ws.append("draft.md", f"\n## {entry.get('name', 'タスク')}\n{body}\n")

    def _draft_body(self) -> str:
        """下書きの本文（ヘッダ行を除いた書き足し部分）を返す。"""
        raw = self.ws.read("draft.md")
        lines = raw.splitlines()
        while lines and (lines[0].startswith("# 成果物下書き")
                         or lines[0].startswith("依頼:")):
            lines.pop(0)
        return "\n".join(lines).strip()

    def summarize(self, user_request: str,
                  results: Optional[List[dict]] = None) -> str:
        # 成果物は下書きの蓄積を「提出」する形を基本にする。
        # 報告役の仕事は全文の生成ではなく、導入を書いて提出すること。
        # 下書きが無い場合だけ、従来どおり台帳から生成する。
        draft = self._draft_body()
        if draft:
            points = "\n".join(f"- {p}" for p in self.points) or "（要点なし）"
            prompt = f"""
依頼に対する作業が終わりました。最終報告の導入だけを書いてください。
本文（各段階が書き足した成果物）はこの後にそのまま続きます。
導入は3〜5行で、要点をもとに何ができたかを伝えてください。
本文の内容を繰り返さないでください。要点に無い事実は書かないでください。

依頼: {user_request}

要点:
{points}
"""
            intro = self.llm.generate("report", prompt)
            return f"{intro.strip()}\n\n---\n\n{draft}"
        # 結果台帳をもとに最終報告をまとめる。
        # 「出力」（事実）を根拠にし、「補足」（実行役の解釈）は参考に留める。
        entries = results if results is not None else self.ledger
        lines = []
        for e in entries:
            line = f"- [{e['name']}] status={e['status']}\n  出力: {e['output'][:400]}"
            if e.get("note"):
                line += f"\n  補足（実行役の解釈）: {e['note'][:200]}"
            lines.append(line)
        joined = "\n".join(lines)
        prompt = f"""
依頼に対する作業が終わりました。結果台帳をもとに、最終報告を短くまとめてください。
「出力」は検証可能な事実、「補足」は実行役の解釈です。報告は出力を根拠にし、
補足だけにしか無い内容は事実として断定しないでください。
結果に無い推測はしないでください。

依頼: {user_request}

結果台帳:
{joined}
"""
        # 最終報告だけは性格付けありの "report" 設定で生成する
        return self.llm.generate("report", prompt)
