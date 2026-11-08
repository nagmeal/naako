import sys

with open("main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'if attempt > 1:' in line:
        new_lines.append(line)
        new_lines.append('                    evolution_prompt += f"\n\n前回の実行エラー:\n{last_error}"\n')
        skip = True
        continue
    if skip:
        if 'suggestion = _chat' in line:
            skip = False
        else:
            continue
    new_lines.append(line)

with open("main.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Successfully fixed syntax error in evolution_prompt += ...")
