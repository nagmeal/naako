import datetime
import os

class WorkspaceManager:
    """
    Manages the shared workspace for Naako and Sabuko.
    Ensures minimal state storage to keep context consumption low.
    """
    def __init__(self, workspace_dir=".workspace"):
        self.workspace_dir = workspace_dir
        self._ensure_workspace_exists()

    def _ensure_workspace_exists(self):
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir)

    def _get_path(self, filename):
        return os.path.join(self.workspace_dir, filename)

    def read(self, filename):
        """Reads the content of a workspace file."""
        path = self._get_path(filename)
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write(self, filename, content):
        """Writes content to a workspace file, overwriting previous content."""
        path = self._get_path(filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def append(self, filename, content):
        """Appends content to a workspace file (used for logs/history)."""
        path = self._get_path(filename)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content + "\n")

    def summarize_file(self, filename, summary_content):
        """Replaces the content of a file with a summarized version."""
        self.write(filename, summary_content)

    def clear(self, filename):
        """Clears the content of a workspace file."""
        self.write(filename, "")

    def rotate_memo(self, request: str = ""):
        """前回の実行メモを archive/ に退避し、今回用の新しいメモを始める。

        メモは1回の実行（依頼）の中ではタスク間で共有するが、
        実行をまたいで残すと前回の内容が混ざって混乱の元になるため、
        実行の開始時に区切る。
        """
        memo_path = self._get_path("memo.txt")
        if os.path.exists(memo_path) and os.path.getsize(memo_path) > 0:
            archive_dir = os.path.join(self.workspace_dir, "archive")
            os.makedirs(archive_dir, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            dest = os.path.join(archive_dir, f"memo-{stamp}.txt")
            n = 1
            while os.path.exists(dest):
                n += 1
                dest = os.path.join(archive_dir, f"memo-{stamp}-{n}.txt")
            os.rename(memo_path, dest)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.write("memo.txt", f"# 実行メモ（{now} 開始）\n依頼: {request}\n")

    def list_files(self):
        """Lists all files currently in the workspace."""
        return os.listdir(self.workspace_dir)

    def delete_workspace(self):
        """Deletes the entire workspace directory."""
        import shutil
        shutil.rmtree(self.workspace_dir)
