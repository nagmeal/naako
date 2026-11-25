import settings
from llm_client import LLMClient
from workspace_manager import WorkspaceManager
from typing import List, Optional


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

    def plan(self, user_request: str, strict: bool = False) -> str:
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
        # 実行の開始で台帳をリセットする（段階の区切り）
        self.ledger = []
        self._save_ledger()
        return plan

    def _save_ledger(self) -> None:
        import json
        self.ws.write("results.json",
                      json.dumps(self.ledger, ensure_ascii=False, indent=1))

    def _ledger_context(self) -> str:
        if not self.ledger:
            return "（まだ結果はありません）"
        lines = []
        for e in self.ledger:
            lines.append(
                f"- [{e['name']}] status={e['status']}\n  出力: {e['output'][:300]}")
        return "\n".join(lines)

    def execute(self, task_description: str, task_type: str,
                skill_name: Optional[str] = None,
                task_name: str = "") -> dict:
        # タスクを1件実行し、結果を台帳に記録して返す。
        # スクリプトを持つスキルでは、台帳の「出力」はスクリプトの生出力
        # （検証可能な事実）とし、モデルの文章は「補足」に分ける。
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
これまでの結果台帳を参考にしてください。{skill_block}

タスク: {task_description}
結果台帳:
{self._ledger_context()}
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
        self.ledger.append(entry)
        self._save_ledger()
        self.ws.append("memo.txt",
                       f"[{task_description}] 完了: {entry['output'][:50]}...")
        return entry

    def summarize(self, user_request: str,
                  results: Optional[List[dict]] = None) -> str:
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
