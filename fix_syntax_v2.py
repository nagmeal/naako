import sys

with open("main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # 169行目あたりの不正な f-string を修正
    if 'evolution_prompt += f"' in line and '前回の実行エラー' not in line:
        # 次の数行を読み飛ばして、1行にまとめる
        # 実際には単純にこの行を正しい形式に置換し、
        # それに続く不正な行を削除する
        new_lines.append('                    evolution_prompt += f"\n\n前回の実行エラー:\n{last_error}"\n')
        continue
    if '前回の実行エラー:' in line or '{last_error}"' in line:
        # evolution_prompt の中身であればスキップ
        if any('evolution_prompt' in l for l in new_lines[-5:]):
            continue
    new_lines.append(line)

with open("main.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
