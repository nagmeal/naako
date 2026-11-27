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
        return plan

    def execute(self, task_description: str, task_type: str,
                skill_name: Optional[str] = None) -> str:
        # タスクを1件実行する。スキル指定があれば手順とスクリプト結果を取り込む。
        memo = self.ws.read("memo.txt")

        skill_block = ""
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
                rc, out = self.skills.run_script(skill_name, input_text)
                skill_block += f"\n\n【スクリプト実行結果 (終了コード {rc})】\n{out}"

        prompt = f"""
以下のタスクを実行してください。
作業メモの内容を参考にしてください。{skill_block}

タスク: {task_description}
作業メモ: {memo}
"""
        result = self.llm.generate("main", prompt)
        self.ws.append("memo.txt", f"[{task_description}] 完了: {result[:50]}...")
        return result

    def summarize(self, user_request: str, results: List[str]) -> str:
        # 全タスクの結果をもとに最終報告をまとめる。
        joined = "\n".join(f"- {r[:200]}" for r in results)
        prompt = f"""
依頼に対する作業が終わりました。各タスクの結果をもとに、最終報告を短くまとめてください。
結果に無い推測はしないでください。

依頼: {user_request}

結果:
{joined}
"""
        return self.llm.generate("main", prompt)
