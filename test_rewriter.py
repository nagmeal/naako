import os
from rewriter import replace_code

def test_replace_code():
    # テスト用のファイルを作成
    test_file = "test_target.py"
    original_content = "def hello():\n    print('Hello World')\n\nprint(hello())"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(original_content)
    
    print(f"--- Test Start ---")
    print(f"Original content:\n{original_content}\n")

    # 置換実行
    old_str = "print('Hello World')"
    new_str = "print('Hello Claude Code!')"
    
    success = replace_code(test_file, old_str, new_str)
    
    if success:
        print("✅ 置換に成功しました。")
        with open(test_file, "r", encoding="utf-8") as f:
            updated_content = f.read()
        print(f"Updated content:\n{updated_content}\n")
        
        if new_str in updated_content:
            print("✅ 内容が正しく更新されています。")
        else:
            print("❌ 内容が更新されていません。")
            
        if os.path.exists(test_file + ".bak"):
            print("✅ バックアップファイルが作成されています。")
    else:
        print("❌ 置換に失敗しました。")

    # 後片付け
    if os.path.exists(test_file): os.remove(test_file)
    if os.path.exists(test_file + ".bak"): os.remove(test_file + ".bak")

if __name__ == "__main__":
    test_replace_code()
