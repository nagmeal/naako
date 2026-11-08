import sys

with open("main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 152行目から177行目あたりを修正 (0-indexed)
# evolution_prompt = ( ... ) の部分をトリプルクォートに書き換える
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'evolution_prompt = (' in line:
        start_idx = i
    if start_idx != -1 and ')' in line and i > start_idx + 10:
        end_idx = i + 1
        break

if start_idx != -1 and end_idx != -1:
    new_prompt = [
        '                # 2. AIに修正案を出させる (SEARCH/REPLACE形式)\n',
        '                evolution_prompt = f"""あなたは自己進化するAIエージェントの設計者です。\n',
        '目標: {goal}\n\n',
        '現在のコード:\n',
        '{current_code}\n\n',
        'このコードを書き換えて目標を達成してください。\n',
        '回答は必ず以下の形式で出力してください。余計な説明は一切不要です。\n',
        '<<<< SEARCH\n',
        '置換前の正確なコードブロック\n',
        '====\n',
        '置換後のコードブロック\n',
        '>>>> REPLACE\n',
        '必ず正確なインデントと文字列を維持して指定してください。\n',
        '"""\n'
    ]
    lines[start_idx:end_idx] = new_prompt
    with open("main.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Successfully fixed evolution_prompt")
else:
    print("Could not find evolution_prompt block")
