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

    def list_files(self):
        """Lists all files currently in the workspace."""
        return os.listdir(self.workspace_dir)

    def delete_workspace(self):
        """Deletes the entire workspace directory."""
        import shutil
        shutil.rmtree(self.workspace_dir)
