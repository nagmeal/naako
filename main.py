import ollama
import os
import re
import shutil
from settings import load_settings
from rewriter import update_setting, replace_code, run_test_script, apply_search_replace

# 初回読み込み
AGENT_SETTINGS, MESSAGES = load_settings()

MODEL = AGENT_SETTINGS["main"]["model"]
SYSTEM_PROMPT = AGENT_SETTINGS["main"]["system_prompt"]
SUBAGENT_SYSTEM_PROMPT = AGENT_SETTINGS["sub"]["default"]["system_prompt"]


def _chat(system_prompt: str, prompt: str) -> str:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"]


def _call_subagent(prompt: str, agent_type: str = "default") -> str:
    """サブエージェントを呼び出し、プロンプトを渡して返答を返す。"""
    # 設定を最新の状態にする
    current_settings, _ = load_settings()
    sub_config = current_settings["sub"].get(agent_type, current_settings["sub"]["default"])
    return _chat(sub_config["system_prompt"], prompt)


def talk_to_naako(prompt: str, use_subagent: bool = True) -> str:
    if not use_subagent:
        # サブエージェントを通さず、なあこが直接回答する
        return _chat(SYSTEM_PROMPT, prompt)

    # タグ [agent_type] を抽出
    tag_match = re.search(r"\[([a-zA-Z0-9_]+)\]", prompt)
    agent_type = tag_match.group(1) if tag_match else "default"

    # タグ部分を削除して純粋な依頼内容にする
    clean_prompt = re.sub(r"\[([a-zA-Z0-9_]+)\]", "", prompt).strip()

    # 1. メインエージェントでプロンプトを英語に翻訳
    translation_prompt = f"以下のユーザー依頼を、サブエージェントに指示するための正確な英語に翻訳してください。翻訳結果のみを出力してください:\n\n{clean_prompt}"
    english_prompt = _chat(SYSTEM_PROMPT, translation_prompt)

    # 2. 翻訳後のプロンプトをサブエージェントに渡す
    sub_result = _call_subagent(english_prompt, agent_type=agent_type)
    summary_prompt = (
        f"ユーザーの依頼:\n{clean_prompt}\n\n"
        f"サブエージェントの処理結果:\n{sub_result}\n\n"
        "上記の処理結果だけを根拠に、依頼への返答を要約してください。"
    )
    return _chat(SYSTEM_PROMPT, summary_prompt)


if __name__ == "__main__":
    print("【エージェント『なあこ』を起動しています...】")
    print("終了するには /bye と入力してください。")
    print("サブエージェントの有効/無効は /subko enable または /subko disable で切り替えられます。\n")

    use_subagent = True
    while True:
        try:
            prompt = input("> ").strip()
        except EOFError:
            break

        if prompt == "/bye":
            print(MESSAGES.get("exit", "バイバイ！"))
            break
        if not prompt:
            continue

        if prompt == "/subko enable":
            use_subagent = True
            print(MESSAGES.get("subko_enable", "サブエージェントを有効にしました。"))
            continue
        if prompt == "/subko disable":
            use_subagent = False
            print(MESSAGES.get("subko_disable", "サブエージェントを無効にしました。"))
            continue
        if prompt == "/subko":
            use_subagent = not use_subagent
            message = MESSAGES.get("subko_enable", "有効") if use_subagent else MESSAGES.get("subko_disable", "無効")
            print(message)
            continue
        if prompt.startswith("/set "):
            parts = prompt.split(" ", 2)
            if len(parts) < 3:
                print("なあこ: 使い方が違いますよー /set パス 値")
                continue
            path_str = parts[1]
            value = parts[2].strip('"')
            key_path = path_str.split(".")
            if update_setting(key_path, value):
                print(f"なあこ: {path_str} を更新しましたよー")
            continue
        if prompt.startswith("/add-agent "):
            parts = prompt.split(" ", 2)
            if len(parts) < 3:
                print("なあこ: 使い方が違いますよー /add-agent 名前 プロンプト")
                continue
            agent_name = parts[1]
            system_prompt = parts[2].strip('"')
            new_config = {
                "model": "gemma4:e4b",
                "system_prompt": system_prompt
            }
            if update_setting(['sub', agent_name], new_config):
                print(f"なあこ: 新しいサブエージェント 『{agent_name}』 を追加しましたよー")
            continue

        if prompt.startswith("/inject "):
            parts = prompt.split('"')
            if len(parts) < 4:
                print("なあこ: 使い方が違いますよー /inject \"古いコード\" \"新しいコード\"")
                continue
            old_code = parts[1]
            new_code = parts[3]
            if replace_code("main.py", old_code, new_code):
                print("なあこ: 自分自身のコードを書き換えましたよー。次回の起動から反映されます。")
            else:
                print("なあこ: 書き換えに失敗しちゃいました...。")
            continue

        if prompt.startswith("/analyze"):
            print("なあこ: 自分自身のコードを分析して、次に何をすべきか考えますねー。")
            files_to_read = ["main.py", "settings.py", "tasks/20261029/Roadmap.md"]
            context = ""
            for file_path in files_to_read:
                try:
                    with open(file_//path, "r", encoding="utf-8") as f:
                        context += f"\n--- {file_path} ---\n{f.read()}\n"
                except FileNotFoundError:
                    context += f"\n--- {file_path} ---\n(ファイルが見つかりませんでした)\n"

            designer_system_prompt = (
                "あなたは自己進化するAIエージェントの設計者です。丁寧な口調ではなく、"
                "技術的な分析レポートとして、客観的かつ具体的に回答してください。"
            )
            analysis_prompt = (
                f"以下の現在のコードベースとロードマップを分析し、目標を達成するために次に実装すべき具体的な機能を1つ提案してください。\n"
                f"提案は、必ず以下の形式で出力してください。余計な挨拶や前置きは不要です。\n\n"
                f"【機能名】: (機能の名前)\n"
                f"【目的】: (なぜこの機能が必要か)\n"
                f"【具体的な実装方針】: (どのようなコードを追加・修正すべきか)\n\n"
                f"【現在のコンテキスト】\n{context}"
            )
            analysis_result = _chat(designer_system_prompt, analysis_prompt)
            print(f"なあこの分析結果:\n\n{analysis_result}\n")
            continue

        if prompt.startswith("/plan "):
            print("なあこ: 分析結果をロードマップに組み込みますねー。")
            parts = prompt.split(" ", 1)
            if len(parts) < 2:
                print("なあこ: 使い方が違いますよー /plan \"機能名: 目的\"")
                continue
            task_description = parts[1].strip('"')
            roadmap_path = "tasks/20261029/Roadmap.md"
            try:
                with open(roadmap_path, "a", encoding="utf-8") as f:
                    f.write(f"\n- [ ] {task_description}\n")
                print(f"なあこ: ロードマップにタスクを追加しましたよー！\n追加内容: {task_description}")
            except Exception as e:
                print(f"なあこ: ロードマップの更新に失敗しちゃいました...。 {e}")
            continue

        if prompt.startswith("/evolve "):
            parts = prompt.split('"')
            if len(parts) < 4:
                print("なあこ: 使い方が違いますよー /evolve \"テストファイル\" \"目標\"")
                continue
            test_file = parts[1]
            goal = parts[3]
            print(f"なあこ: {goal} のために、自律進化を開始しますねー。")
            max_attempts = 5
            last_error = ""
            for attempt in range(1, max_attempts + 1):
                print(f"（試行 {attempt}/{max_attempts}回目...）")
                with open("main.py", "r", encoding="utf-8") as f:
                    current_code = f.read()
                evolution_prompt = f"""あなたは自己進化するAIエージェントの設計者です。
目標: {goal}
現在のコード:
{current_code}
このコードを書き換えて目標を達成してください。
回答は必ず以下の形式で出力してください。余計な説明は一切不要です。
<<<< SEARCH
置換前の正確なコードブロック
====
置換後のコードブロック
>>>> REPLACE
必ず正確なインデントと文字列を維持して指定してください。
"""
                if attempt > 1:
                    evolution_prompt += f"\\n\\n前回の実行エラー:\\n{last_error}"
                suggestion = _chat(SYSTEM_PROMPT, evolution_prompt)
                search_match = re.search(r"<<<< SEARCH\n(.*?)\n====\n(.*?)\n>>>> REPLACE", suggestion, re.DOTALL)
                if not search_match:
                    print("なあこ: 修正案の形式が正しくなかったです...。リトライしますね。")
                    continue
                search_block = search_match.group(1)
                replace_block = search_match.group(2)
                if apply_search_replace("main.py", search_block, replace_block):
                    success, output = run_test_script(test_file)
                    if success:
                        print(f"なあこ: やったー！ {attempt}回目で目標を達成しましたよー！")
                        print(f"テスト結果:\n{output}")
                        break
                    else:
                        print(f"なあこ: まだエラーが出ちゃいました...。")
                        last_error = output
                else:
                    print("なあこ: コードの置換に失敗しました。")
                    last_error = "Replace failed: search block not found in file."
            else:
                print("なあこ: 5回頑張りましたが、ダメでした...。諦めてロールバックします。")
                if os.path.exists("main.py.bak"):
                    shutil.copy2("main.py.bak", "main.py")
            continue

        if prompt.startswith("/evolve-auto"):
            print("なあこ: 完全自律進化モードを開始しますねー。目標を達成するまで、分析・計画・実装を繰り返しますよー！")
            while True:
                print("\n--- [自律サイクル: 分析フェーズ] ---")
                files_to_read = ["main.py", "settings.py", "tasks/20261029/Roadmap.md"]
                context = ""
                for file_path in files_to_read:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            context += f"\n--- {file_path} ---\n{f.read()}\n"
                    except FileNotFoundError:
                        context += f"\n--- {file_path} ---\n(ファイルが見つかりませんでした)\n"
                designer_system_prompt = (
                    "あなたは自己進化するAIエージェントの設計者です。丁寧な口調ではなく、"
                    "技術的な分析レポートとして、客観的かつ具体的に回答してください。"
                )
                analysis_prompt = (
                    f"以下の現在のコードベースとロードマップを分析し、目標を達成するために次に実装すべき具体的な機能を1つ提案してください。\n"
                    f"提案は、必ず以下の形式で出力してください。余計な挨拶や前置きは不要です。\n\n"
                    f"【機能名】: (機能の名前)\n"
                    f"【目的】: (なぜこの機能が必要か)\n"
                    f"【具体的な実装方針】: (どのようなコードを追加・修正すべきか)\n\n"
                    f"【現在のコンテキスト】\n{context}"
                )
                analysis_result = _chat(designer_system_prompt, analysis_prompt)
                print(f"分析結果:\n{analysis_result}")
                print("\n--- [自律サイクル: 計画フェーズ] ---")
                name_match = re.search(r"【機能名】: (.*)", analysis_result)
                purpose_match = re.search(r"【目的】: (.*)", analysis_result)
                if not name_match or not purpose_match:
                    print("なあこ: 分析結果からタスクを抽出できませんでした。リトライします。")
                    continue
                task_name = name_match.group(1).strip()
                task_purpose = purpose_match.group(1).strip()
                task_description = f"{task_name}: {task_purpose}"
                roadmap_path = "tasks/20261029/Roadmap.md"
                try:
                    with open(roadmap_path, "a", encoding="utf-8") as f:
                        f.write(f"\n- [ ] {task_description}\n")
                    print(f"ロードマップにタスクを追加しました: {task_description}")
                except Exception as e:
                    print(f"ロードマップ更新失敗: {e}")
                    continue
                print("\n--- [自律サイクル: 実装フェーズ] ---")
                impl_prompt = f"機能名: {task_name}\n目的: {task_purpose}\n実装方針: {analysis_result}"
                test_file = "test_evolve.py"
                max_attempts = 5
                last_error = ""
                evolved_successfully = False
                for attempt in range(1, max_attempts + 1):
                    print(f"（実装試行 {attempt}/{max_attempts}回目...）")
                    with open("main.py", "r", encoding="utf-8") as f:
                        current_code = f.read()
                    evolution_prompt = f"""あなたは自己進化するAIエージェントの設計者です。
目標: {impl_prompt}
現在のコード:
{current_code}
このコードを書き換えて目標を達成してください。
回答は必ず以下の形式で出力してください。余計な説明は一切不要です。
<<<< SEARCH
置換前の正確なコードブロック
====
置換後のコードブロック
>>>> REPLACE
必ず正確なインデントと文字列を維持して指定してください。
"""
                    if attempt > 1:
                        evolution_prompt += f"\\n\\n前回の実行エラー:\\n{last_error}"
                    suggestion = _chat(SYSTEM_PROMPT, evolution_prompt)
                    search_match = re.search(r"<<<< SEARCH\n(.*?)\n====\n(.*?)\n>>>> REPLACE", suggestion, re.DOTALL)
                    if not search_match:
                        continue
                    if apply_search_replace("main.py", search_match.group(1), search_match.group(2)):
                        success, output = run_test_script(test_file)
                        if success:
                            print(f"実装成功！ {attempt}回目で目標を達成しました。")
                            evolved_successfully = True
                            break
                        else:
                            last_error = output
                if evolved_successfully:
                    print("自律進化ステップが完了しました。次の改善を探します。")
                else:
                    print("今回の実装は断念しました。ロールバックして次を考えます。")
                    if os.path.exists("main.py.bak"):
                        shutil.copy2("main.py.bak", "main.py")
                print("\n次のサイクルを開始しますか？ (y/n)")
                try:
                    choice = input("> ").strip().lower()
                except EOFError:
                    break
                if choice != 'y':
                    print("自律進化モードを終了します。")
                    break
            continue

        reply = talk_to_naako(prompt, use_subagent=use_subagent)
        print(f"なあこ: \n{reply}\n")
