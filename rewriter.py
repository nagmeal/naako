import pprint
import os
import shutil
import ast
import subprocess
import re

def update_setting(key_path: list, value: any):
    """
    設定ファイルの指定したパスの値を更新する。
    key_path: ['sub', 'researcher', 'system_prompt'] のようなリスト
    """
    from settings import load_settings

    # 現在の設定を読み込む
    AGENT_SETTINGS, MESSAGES = load_settings()

    # 値を更新
    target = AGENT_SETTINGS
    for key in key_path[:-1]:
        target = target[key]
    target[key_path[-1]] = value

    # 保存
    with open("settings.py", "w", encoding="utf-8") as f:
        f.write("# Agent Settings\n\n")
        f.write(f"AGENT_SETTINGS = {pprint.pformat(AGENT_SETTINGS, indent=4)}\n\n")
        f.write(f"MESSAGES = {pprint.pformat(MESSAGES, indent=4)}\n\n")
        f.write("def load_settings():\n")
        f.write("    \"\"\"設定ファイルを動的に読み込む。\"\"\"\n")
        f.write("    import importlib\n")
        f.write("    import settings\n")
        f.write("    importlib.reload(settings)\n")
        f.write("    return settings.AGENT_SETTINGS, settings.MESSAGES\n")

    return True

def verify_syntax(file_path: str) -> bool:
    """
    ファイルのPython構文が正しいか検証する。
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source)
        return True
    except Exception as e:
        print(f"Syntax Error in {file_path}: {e}")
        return False

def run_test_script(script_path: str) -> tuple[bool, str]:
    """
    指定したテストスクリプトを実行し、成否と出力を返す。
    """
    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8"
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def apply_search_replace(file_path: str, search_block: str, replace_block: str) -> bool:
    """
    SEARCH/REPLACE形式のブロックを適用してファイルを更新する。
    部分的に一致する箇所を探し、置換する。
    """
    bak_path = file_path + ".bak"
    try:
        shutil.copy2(file_path, bak_path)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if search_block not in content:
            print(f"Error: SEARCHブロックが見つかりませんでした ({file_path})")
            return False

        new_content = content.replace(search_block, replace_block, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        if not verify_syntax(file_path):
            print(f"❌ 構文エラーを検知しました。ロールバックします。")
            shutil.copy2(bak_path, file_path)
            return False

        return True
    except Exception as e:
        print(f"Error during search-replace: {e}")
        if os.path.exists(bak_path):
            shutil.copy2(bak_path, file_path)
        return False

def replace_code(file_path: str, old_string: str, new_string: str) -> bool:
    """
    （互換性のために維持）単純な文字列置換を行う。
    """
    return apply_search_replace(file_path, old_string, new_string)
