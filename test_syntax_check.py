import os
from rewriter import replace_code

def test_syntax_rollback():
    test_file = "test_syntax.py"
    original_content = "def hello():\n    print('Correct')\n"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(original_content)
    
    print("--- Test Start: Syntax Error Case ---")
    
    # あえて構文エラーになるコードに置換する (コロンを消すなど)
    old_str = "def hello():"
    new_str = "def hello" # 構文エラー
    
    print(f"Attempting to replace '{old_str}' with '{new_str}'...")
    success = replace_code(test_file, old_str, new_str)
    
    if not success:
        print("✅ 構文エラーを検知し、置換が失敗した（想定通り）。")
        with open(test_file, "r", encoding="utf-8") as f:
            current_content = f.read()
        if current_content == original_content:
            print("✅ コードが元の状態にロールバックされています。")
        else:
            print("❌ ロールバックが正しく行われていません。")
    else:
        print("❌ 構文エラーがあるにもかかわらず、置換に成功してしまいました。")

    # 後片付け
    if os.path.exists(test_file): os.remove(test_file)
    if os.path.exists(test_file + ".bak"): os.remove(test_file + ".bak")

if __name__ == "__main__":
    test_syntax_rollback()
