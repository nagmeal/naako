import os

def update_setting(key_path: list, value: any):
    """
    設定ファイルの指定したパスの値を更新する。
    key_path: ['sub', 'researcher', 'system_prompt'] のようなリスト
    """
    import settings
    import ast

    with open("settings.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 簡易的な実装として、AGENT_SETTINGS という変数を ast で解析して書き換える
    # 実際には、設定ファイル全体の構造を維持しつつ、特定の値を置換する必要がある
    
    # ここでは、settings.py を Python ファイルとして読み込み、
    # 辞書を更新して、再び書き出すアプローチを取る
    
    # 注意: settings.py には AGENT_SETTINGS と MESSAGES がある
    # 文字列置換ではリスクがあるため、一度 import して辞書を更新し、
    # 形式を整えて保存する。
    
    # 今回は、ロードマップの「泥臭い実装」に従い、
    # 辞書を文字列として書き出すシンプルな方法を実装する。
    
    import pprint
    
    # 現在の設定を読み込む
    # settings.py を直接 import すると、以前の書き換えで MESSAGES が消えている可能性があるため
    # load_settings を使用して最新の状態を取得する
    from settings import load_settings
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

# テスト用
if __name__ == "__main__":
    update_setting(['sub', 'default', 'system_prompt'], "テスト用のプロンプトです")
    print("設定を更新しました。")
