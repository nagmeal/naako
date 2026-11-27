import re
import sys

import settings
from llm_client import LLMClient
from workspace_manager import WorkspaceManager
from agents import NaakoAgent
from skills import SkillLoader

MAX_STEPS = 10  # 1回の依頼で実行するタスク数の上限


class SimpleEngine:
    """
    単一ループの実行エンジン。
    計画 → 実行（スキル対応） → 要約、だけを行う。
    """
    def __init__(self, excluded_skills=None):
        self.llm = LLMClient()
        self.ws = WorkspaceManager()
        self.skills = SkillLoader(getattr(settings, "SKILLS_DIR", "skills"),
                                  exclude=set(excluded_skills or ()))
        self.naako = NaakoAgent(self.llm, self.ws, self.skills)

    def parse_plan(self, plan_text: str):
        """
        計画テキストをタスクのリストに変換する。
        形式: 1. [タスク名] 内容 (タイプ: nlp/code) [(スキル: name)]
        小さいモデルは [タスク名] を落とすことがあるので、括弧なしも許容する。
        """
        tasks = []
        for line in plan_text.strip().split("\n"):
            match = re.search(
                r"\d+\.\s+(?:\[(.*?)\]\s+)?(.*?)\s+\(タイプ:\s*(nlp|code)\)"
                r"(?:\s+\(スキル:\s*([a-z0-9-]+)\))?", line)
            if match:
                tasks.append({
                    "name": match.group(1) or f"タスク{len(tasks) + 1}",
                    "description": match.group(2),
                    "type": match.group(3),
                    "skill": match.group(4),
                })
        return tasks

    def run(self, user_request: str) -> str | None:
        """依頼を1件実行し、最終報告の文字列を返す（失敗時は None）。"""
        print(f"🚀 依頼を受信しました: {user_request}")

        # 実行ごとにメモを区切る（前回のメモは archive/ に退避）
        self.ws.rotate_memo(user_request)

        print("\n[計画] なあこが計画を立てています...")
        plan_text = self.naako.plan(user_request)
        print(f"計画:\n{plan_text}")

        tasks = self.parse_plan(plan_text)
        if not tasks:
            # 形式が崩れていたら、厳しめの指示でもう一度だけ計画させる
            print("⚠️ 計画を読み取れなかったため、形式を厳しくして再計画します。")
            plan_text = self.naako.plan(user_request, strict=True)
            print(f"計画:\n{plan_text}")
            tasks = self.parse_plan(plan_text)
        if not tasks:
            print("⚠️ 計画を読み取れませんでした。")
            return None
        if len(tasks) > MAX_STEPS:
            print(f"⚠️ タスクが {len(tasks)} 件あるため、先頭 {MAX_STEPS} 件だけ実行します。")
            tasks = tasks[:MAX_STEPS]

        results = []
        for i, task in enumerate(tasks, 1):
            skill_note = f" (スキル: {task['skill']})" if task.get("skill") else ""
            print(f"\n[実行 {i}/{len(tasks)}] 「{task['name']}」{skill_note} を実行中...")
            entry = self.naako.execute(task["description"], task["type"],
                                       task.get("skill"), task["name"])
            print(f"結果: {entry['output'][:100]}...")
            if entry["status"] == "error":
                print("⚠️ このタスクはエラーで終わりました（結果台帳に記録済み）。")
            results.append(entry)

        print("\n[報告] なあこがまとめています...")
        summary = self.naako.summarize(user_request, results)
        print(f"\n✨ 完了報告:\n{summary}")
        return summary


if __name__ == "__main__":
    engine = SimpleEngine()
    if len(sys.argv) > 1:
        # 引数があれば1回だけ実行: python main.py "依頼文"
        engine.run(" ".join(sys.argv[1:]))
    else:
        # 引数なしは対話モード（/bye で終了）
        print("なあこ: ご依頼をどうぞ（/bye で終了します）")
        while True:
            try:
                user_input = input("あなた: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user_input in ("/bye", "exit", "quit"):
                print(settings.MESSAGES["exit"])
                break
            if user_input:
                engine.run(user_input)
