import sys

with open("main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 137行目から208行目までを置換 (0-indexed なので 136から208まで)
# 実際には if prompt.startswith("/evolve "): から continue までのブロック
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'if prompt.startswith("/evolve "):' in line:
        start_idx = i
    if i > start_idx and 'continue' in line and i > 200: # ブロックの終わりを探す
        end_idx = i + 1
        break

if start_idx != -1 and end_idx != -1:
    new_block = [
        '        if prompt.startswith("/evolve "):\n',
        '            # /evolve "test_script.py" "目標"\n',
        '            parts = prompt.split(\'"\')\n',
        '            if len(parts) < 4:\n',
        '                print("なあこ: 使い方が違いますよー /evolve \\"テストファイル\\" \\"目標\\"")\n',
        '                continue\n',
        '            test_file = parts[1]\n',
        '            goal = parts[3]\n',
        '            print(f"なあこ: {goal} のために、自律進化を開始しますねー。")\n',
        '            max_attempts = 5\n',
        '            last_error = ""\n',
        '            for attempt in range(1, max_attempts + 1):\n',
        '                print(f"（試行 {attempt}/{max_attempts}回目...）")\n',
        '                with open("main.py", "r", encoding="utf-8") as f:\n',
        '                    current_code = f.read()\n',
        '                evolution_prompt = (\n',
        '                    f"あなたは自己進化するAIエージェントの設計者です。\n"\n',
        '                    f"目標: {goal}\n\n"\n',
        '                    f"現在のコード:\n{current_code}\n\n"\n',
        '                    f"このコードを書き換えて目標を達成してください。\n"\n',
        '                    f"回答は必ず以下の形式で出力してください。余計な説明は一切不要です。\n"\n',
        '                    f"<<<< SEARCH\n"\n',
        '                    f"置換前の正確なコードブロック\n"\n',
        '                    f"====\n"\n',
        '                    f"置換後のコードブロック\n"\n',
        '                    f">>>> REPLACE\n"\n',
        '                    f"必ず正確なインデントと文字列を維持して指定してください。"\n',
        '                )\n',
        '                if attempt > 1:\n',
        '                    evolution_prompt += f"\n\n前回の実行エラー:\n{last_error}"\n',
        '                suggestion = _chat(SYSTEM_PROMPT, evolution_prompt)\n',
        '                import re\n',
        '                search_match = re.search(r"<<<< SEARCH\n(.*?)\n====\n(.*?)\n>>>> REPLACE", suggestion, re.DOTALL)\n',
        '                if not search_match:\n',
        '                    print("なあこ: 修正案の形式が正しくなかったです...。リトライしますね。")\n',
        '                    continue\n',
        '                search_block = search_match.group(1)\n',
        '                replace_block = search_match.group(2)\n',
        '                from rewriter import apply_search_replace\n',
        '                if apply_search_replace("main.py", search_block, replace_block):\n',
        '                    success, output = run_test_script(test_file)\n',
        '                    if success:\n',
        '                        print(f"なあこ: やったー！ {attempt}回目で目標を達成しましたよー！")\n',
        '                        print(f"テスト結果:\n{output}")\n',
        '                        break\n',
        '                    else:\n',
        '                        print(f"なあこ: まだエラーが出ちゃいました...。")\n',
        '                        last_error = output\n',
        '                else:\n',
        '                    print("なあこ: コードの置換に失敗しました。")\n',
        '                    last_error = "Replace failed: search block not found in file."\n',
        '            else:\n',
        '                print("なあこ: 5回頑張りましたが、ダメでした...。諦めてロールバックします。")\n',
        '                import shutil\n',
        '                if os.path.exists("main.py.bak"):\n',
        '                    shutil.copy2("main.py.bak", "main.py")\n',
        '            continue\n'
    ]
    lines[start_idx:end_idx] = new_block
    with open("main.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Successfully updated main.py")
else:
    print("Could not find the evolve block")
