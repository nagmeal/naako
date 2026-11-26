"""なあこ API サーバー（標準ライブラリのみ）

使い方:
    python api_server.py

環境変数:
    NAAKO_API_TOKEN   トークン認証の値。未設定なら 127.0.0.1 のみに強制する
    NAAKO_API_HOST    待ち受けホスト（既定 127.0.0.1）
    NAAKO_API_PORT    待ち受けポート（既定 8765）
    NAAKO_API_MODEL   API モードで使うローカルモデル（既定 gemma4:e4b）
    NAAKO_API_EXCLUDE 封印するスキル（カンマ区切り、既定 code-agent）

API モードの決まり（2026-11-25 設計）:
    - モデルはローカル固定（クラウドに仕事のテキストを出さない）
    - code-agent は封印（カタログから除外し、計画に現れても実行しない）
    - 同時実行は1つ（.workspace を共有するためキューで直列化）

エンドポイント:
    POST /run              {request} → {job_id}（202）
    GET  /jobs/{id}        状態＋報告＋結果台帳
    GET  /jobs             最近のジョブ一覧
    GET  /wiki             wiki 目次
    GET  /wiki/pages/{slug} ページ本文
    GET  /health           稼働状態・モデル・有効スキル
認証: トークン設定時は全リクエストに X-Naako-Token ヘッダーが要る。
"""
import contextlib
import io
import json
import os
import queue
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import settings
from main import SimpleEngine

ROOT = Path(__file__).resolve().parent
TOKEN = os.environ.get("NAAKO_API_TOKEN", "")
HOST = os.environ.get("NAAKO_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("NAAKO_API_PORT", "8765"))
API_MODEL = os.environ.get("NAAKO_API_MODEL", "gemma4:e4b")
EXCLUDED = {s.strip() for s in
            os.environ.get("NAAKO_API_EXCLUDE", "code-agent").split(",")
            if s.strip()}
MAX_REQUEST_CHARS = 8000

# API モードではローカルモデルを使う（main / report 両方）
settings.AGENT_SETTINGS["main"]["model"] = API_MODEL
if "report" in settings.AGENT_SETTINGS:
    settings.AGENT_SETTINGS["report"]["model"] = API_MODEL

ENGINE = SimpleEngine(excluded_skills=EXCLUDED)
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
JOB_QUEUE: "queue.Queue[str]" = queue.Queue()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_ledger() -> list:
    p = ROOT / ".workspace" / "results.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def worker() -> None:
    """ジョブを1件ずつ直列に実行するワーカー。"""
    while True:
        job_id = JOB_QUEUE.get()
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "running"
            job["started_at"] = now_iso()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                report = ENGINE.run(job["request"])
            with JOBS_LOCK:
                job["log"] = buf.getvalue()[-4000:]
                job["ledger"] = read_ledger()
                if report:
                    job["status"] = "done"
                    job["report"] = report
                else:
                    job["status"] = "error"
                    job["error"] = "計画を読み取れませんでした。"
        except Exception as e:  # エンジン例外でもサーバーは落とさない
            with JOBS_LOCK:
                job["log"] = buf.getvalue()[-4000:]
                job["status"] = "error"
                job["error"] = f"{type(e).__name__}: {e}"
        with JOBS_LOCK:
            job["finished_at"] = now_iso()
        JOB_QUEUE.task_done()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 既定のアクセスログは止める
        pass

    def _send(self, code: int, obj, ctype: str = "application/json") -> None:
        if isinstance(obj, (dict, list)):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        else:
            body = str(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not TOKEN:
            return True
        return self.headers.get("X-Naako-Token") == TOKEN

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            # 簡単な UI（静的 HTML。データ取得は各 API 呼び出しで認証する）
            p = ROOT / "ui.html"
            if not p.is_file():
                return self._send(404, {"error": "ui not found"})
            return self._send(200, p.read_text(encoding="utf-8"), "text/html")
        if not self._authorized():
            return self._send(401, {"error": "unauthorized"})
        if path == "/health":
            return self._send(200, {
                "ok": True, "model": API_MODEL,
                "skills": sorted(ENGINE.skills.skills.keys()),
                "excluded_skills": sorted(EXCLUDED),
            })
        if path == "/jobs":
            with JOBS_LOCK:
                items = [{k: j.get(k) for k in
                          ("id", "request", "status", "created_at",
                           "started_at", "finished_at")}
                         for j in list(JOBS.values())[-20:]]
            return self._send(200, items)
        if path.startswith("/jobs/"):
            job_id = path[len("/jobs/"):]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if job is None:
                return self._send(404, {"error": "job not found"})
            return self._send(200, job)
        if path == "/wiki":
            p = ROOT / "wiki" / "index.md"
            if not p.is_file():
                return self._send(404, {"error": "wiki not found"})
            return self._send(200, p.read_text(encoding="utf-8"),
                              "text/markdown")
        if path.startswith("/wiki/pages/"):
            slug = unquote(path[len("/wiki/pages/"):])
            if "/" in slug or "\\" in slug or ".." in slug:
                return self._send(400, {"error": "bad slug"})
            name = slug if slug.endswith(".md") else slug + ".md"
            p = ROOT / "wiki" / "pages" / name
            if not p.is_file():
                return self._send(404, {"error": "page not found"})
            return self._send(200, p.read_text(encoding="utf-8"),
                              "text/markdown")
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._authorized():
            return self._send(401, {"error": "unauthorized"})
        path = urlparse(self.path).path
        if path != "/run":
            return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._send(400, {"error": "invalid json"})
        request = str(data.get("request", "")).strip()
        if not request:
            return self._send(400, {"error": "request is empty"})
        if len(request) > MAX_REQUEST_CHARS:
            return self._send(400, {"error": "request too long"})
        job_id = uuid.uuid4().hex[:12]
        with JOBS_LOCK:
            JOBS[job_id] = {
                "id": job_id, "request": request, "status": "queued",
                "created_at": now_iso(), "started_at": None,
                "finished_at": None, "report": None, "ledger": None,
                "error": None, "log": "",
            }
        JOB_QUEUE.put(job_id)
        return self._send(202, {"job_id": job_id})


def main() -> None:
    host = HOST
    if not TOKEN and host != "127.0.0.1":
        print("⚠️ トークン未設定のため、待ち受けを 127.0.0.1 に強制します。")
        host = "127.0.0.1"
    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer((host, PORT), Handler)
    print(f"なあこ API: http://{host}:{PORT} "
          f"(model={API_MODEL}, excluded={sorted(EXCLUDED)}, "
          f"auth={'on' if TOKEN else 'off'})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
