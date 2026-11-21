import settings
from llm_client import LLMClient
from workspace_manager import WorkspaceManager
from typing import List, Dict, Optional

class NaakoAgent:
    """
    Main Agent 'Naako' (なあこ)
    Role: Orchestrator, Planner, and Evaluator.
    """
    def __init__(self, llm_client: LLMClient, workspace: WorkspaceManager, skills=None):
        self.llm = llm_client
        self.ws = workspace
        self.skills = skills
        self.name = settings.AGENT_SETTINGS["main"]["name"]

    def plan_task(self, user_request: str):
        """
        Decomposes the user request into a series of minimal sub-tasks.
        Updates the workspace plan.txt.
        """
        prompt = f"""
ユーザーからの依頼を分析し、最小単位のタスクに分解して計画を立ててください。
各タスクは「さぶこ」が一度に実行できる最小限の範囲にしてください。

依頼: {user_request}

出力形式:
1. [タスク名] 内容 (タイプ: nlp/code)
2. [タスク名] 内容 (タイプ: nlp/code)
...
"""
        if self.skills and self.skills.catalog_text():
            prompt += f"""

利用可能なスキル（役立つタスクには行末に (スキル: スキル名) を付けること）:
{self.skills.catalog_text()}
"""
        plan = self.llm.generate("main", prompt)
        self.ws.write("plan.txt", plan)
        return plan

    def evaluate_result(self, task_name: str, result: str):
        """
        Evaluates the result of a sub-task.
        Returns True if successful, False otherwise.
        """
        prompt = f"""
タスク「{task_name}」の結果を評価してください。
期待される成果が得られているか判断し、「成功」か「失敗」で始めてください。
失敗の場合は、簡潔に理由を添えてください。

結果: {result}
"""
        evaluation = self.llm.generate("main", prompt)
        return evaluation.startswith("成功")

    def adjust_plan(self, failed_task: str, error_msg: str):
        """
        Adjusts the plan based on failure.
        """
        current_plan = self.ws.read("plan.txt")
        prompt = f"""
以下の計画のタスク「{failed_task}」が失敗しました。
理由: {error_msg}

この失敗を踏まえて、計画を修正してください。
修正後の計画全体を出力してください。

現在の計画:
{current_plan}
"""
        new_plan = self.llm.generate("main", prompt)
        self.ws.write("plan.txt", new_plan)
        return new_plan

    def compress_context(self, filename: str):
        """
        Summarizes the content of a workspace file to keep it minimal.
        """
        content = self.ws.read(filename)
        if not content:
            return

        prompt = f"""
以下の作業記録を、重要な情報のみを保持したまま極限まで簡潔に要約してください。
冗長な表現はすべて排除し、箇条書きでまとめてください。

内容:
{content}
"""
        summary = self.llm.generate("main", prompt)
        self.ws.summarize_file(filename, summary)
        print(f"✨ {filename} のコンテキストを圧縮しました。")

class SabukoAgent:
    """
    Sub Agent 'Sabuko' (さぶこ)
    Role: Executor.
    """
    def __init__(self, llm_client: LLMClient, workspace: WorkspaceManager, skills=None):
        self.llm = llm_client
        self.ws = workspace
        self.skills = skills
        self.name = settings.AGENT_SETTINGS["sub"]["name"]

    def execute_task(self, task_description: str, task_type: str, skill_name: str = None):
        """
        Executes a single minimal task.
        """
        # Sabuko reads the current memo for context
        memo = self.ws.read("memo.txt")

        # スキル指定があれば、手順（SKILL.md本文）とスクリプト実行結果を取り込む
        skill_block = ""
        if skill_name and self.skills:
            body = self.skills.load_body(skill_name)
            if body:
                skill_block += f"\n\n【スキル手順: {skill_name}】\n{body}"
            skill = self.skills.get(skill_name)
            if skill and skill.script:
                rc, out = self.skills.run_script(skill_name, task_description)
                skill_block += f"\n\n【スクリプト実行結果 (終了コード {rc})】\n{out}"

        prompt = f"""
以下のタスクを実行してください。
作業メモの内容を参考にしてください。{skill_block}

タスク: {task_description}
作業メモ: {memo}
"""
        result = self.llm.generate("sub", prompt, task_type=task_type)
        
        # Sabuko updates the memo with minimal findings
        self.ws.append("memo.txt", f"[{task_description}] 完了: {result[:50]}...") 
        
        return result
