import main
import sys

def test():
    try:
        if hasattr(main, 'evolved_feature'):
            if main.evolved_feature() is True:
                print("SUCCESS")
                sys.exit(0)
            else:
                print("FAILURE: function returned wrong value")
                sys.exit(1)
        else:
            print("FAILURE: function not found")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test()
