"""なあこ API のスモークテスト（標準ライブラリのみ）

固定リクエストを投げ、報告が返ることと結果台帳の status が
すべて ok であることを確認して PASS / FAIL を出す。
プロンプトやスキルを変更したときの回帰確認用。

環境変数:
    NAAKO_API_URL    既定 http://127.0.0.1:8765
    NAAKO_API_TOKEN  トークン（サーバー側と合わせる）

使い方: python scripts/api_smoke.py
"""
import json
import os
import sys
import time
import urllib.request

BASE = os.environ.get("NAAKO_API_URL", "http://127.0.0.1:8765")
TOKEN = os.environ.get("NAAKO_API_TOKEN", "")
REQUEST_TEXT = "短い挨拶文を2つ考えて"
TIMEOUT_SECONDS = 600


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("X-Naako-Token", TOKEN)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    try:
        health = call("GET", "/health")
    except Exception as e:
        print(f"FAIL: /health に接続できません（{e}）")
        return 1
    print(f"health: model={health.get('model')} skills={health.get('skills')}")
    if "code-agent" in (health.get("skills") or []):
        print("FAIL: code-agent が封印されていません")
        return 1
    job = call("POST", "/run", {"request": REQUEST_TEXT})
    job_id = job["job_id"]
    print(f"job: {job_id} を投入、完了待ち...")
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        state = call("GET", f"/jobs/{job_id}")
        if state["status"] in ("done", "error"):
            break
        time.sleep(2)
    else:
        print(f"FAIL: {TIMEOUT_SECONDS}秒で終わりませんでした")
        return 1
    if state["status"] != "done":
        print(f"FAIL: status={state['status']} error={state.get('error')}")
        return 1
    if not (state.get("report") or "").strip():
        print("FAIL: 報告が空です")
        return 1
    ledger = state.get("ledger") or []
    bad = [e for e in ledger if e.get("status") != "ok"]
    if bad:
        print(f"FAIL: 台帳に ok でないエントリがあります: {bad}")
        return 1
    print(f"台帳: {len(ledger)}件すべて ok")
    print("報告:")
    print(state["report"])
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
