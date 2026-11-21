import settings
from llm_client import LLMClient
from workspace_manager import WorkspaceManager
from agents import NaakoAgent, SabukoAgent
from skills import SkillLoader
import re

class PDCAEngine:
    """
    The core engine that drives the automated PDCA cycle.
    Plan -> Do -> Check -> Act.
    """
    def __init__(self):
        self.llm = LLMClient()
        self.ws = WorkspaceManager()
        self.skills = SkillLoader(getattr(settings, "SKILLS_DIR", "skills"))
        self.naako = NaakoAgent(self.llm, self.ws, self.skills)
        self.sabuko = SabukoAgent(self.llm, self.ws, self.skills)
        self.max_iterations = 100

    def parse_plan(self, plan_text: str):
        """
        Parses the plan text into a list of executable tasks.
        Format expected: 1. [Task Name] Description (タイプ: nlp/code)
        """
        tasks = []
        lines = plan_text.strip().split('\n')
        for line in lines:
            match = re.search(r'\d+\.\s+\[(.*?)\]\s+(.*?)\s+\(タイプ:\s*(nlp|code)\)(?:\s+\(スキル:\s*([a-z0-9-]+)\))?', line)
            if match:
                tasks.append({
                    "name": match.group(1),
                    "description": match.group(2),
                    "type": match.group(3),
                    "skill": match.group(4)
                })
        return tasks

    def run(self, user_request: str):
        print(f"🚀 依頼を受信しました: {user_request}")
        
        # Initial Plan
        print("\n[Plan] なあこが計画を立てています...")
        plan_text = self.naako.plan_task(user_request)
        print(f"計画案:\n{plan_text}")

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n--- PDCA サイクル {iteration}回目 ---")
            
            tasks = self.parse_plan(self.ws.read("plan.txt"))
            if not tasks:
                print("有効なタスクが見つかりませんでした。計画を再策定します。")
                self.naako.plan_task(user_request)
                continue

            all_success = True
            for task in tasks:
                print(f"\n[Do] さぶこがタスク「{task['name']}」を実行中...")
                result = self.sabuko.execute_task(task['description'], task['type'], task.get('skill'))
                print(f"結果: {result[:100]}...")

                print(f"[Check] なあこが結果を評価中...")
                if self.naako.evaluate_result(task['name'], result):
                    print("✅ 成功")
                else:
                    print("❌ 失敗")
                    all_success = False
                    
                    print(f"[Act] なあこが計画を修正しています...")
                    # We stop current task list and adjust the plan immediately
                    self.naako.adjust_plan(task['name'], result)
                    print(f"修正後の計画:\n{self.ws.read('plan.txt')}")
                    break # Exit task loop to restart with new plan
            
            # Context compression after each cycle to prevent bloat
            if iteration % 5 == 0 or not all_success:
                self.naako.compress_context("memo.txt")
            
            if all_success:
                print("\n✨ すべてのタスクが成功しました！")
                return True
        
        print("\n⚠️ 最大試行回数に達しましたが、完了しませんでした。")
        return False

if __name__ == "__main__":
    engine = PDCAEngine()
    user_input = "Pythonで簡単なTODOリストアプリを作ってください" # Example request
    engine.run(user_input)
