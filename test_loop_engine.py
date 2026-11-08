from rewriter import run_test_script

def test_error_capture():
    print("--- Testing Error Capture ---")
    success, output = run_test_script("test_fail.py")
    
    if not success:
        print("✅ 正常にエラーを検知しました。")
        print(f"回収したエラーログ:\n{output}")
        if "NameError" in output:
            print("✅ 正しいエラー種別（NameError）が回収されています。")
        else:
            print("❌ エラーログに NameError が含まれていません。")
    else:
        print("❌ エラーが発生すべきでしたが、成功してしまいました。")

if __name__ == "__main__":
    test_error_capture()
