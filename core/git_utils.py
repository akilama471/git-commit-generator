import os
import subprocess
import tempfile
from typing import List, Optional, Tuple


class GitDiff:
    def __init__(self, diff: str, staged: bool, files: List[str]):
        self.diff = diff
        self.staged = staged
        self.files = files


def run_git_command(cmd: List[str]) -> Tuple[str, str, int]:
    """Run a git command and return output with UTF-8 encoding"""
    try:
        # Force UTF-8 encoding for git output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",  # Force UTF-8 encoding
            errors="replace",  # Replace invalid characters instead of crashing
            shell=True,
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode
    except Exception as e:
        return "", str(e), 1


def get_staged_diff() -> Optional[GitDiff]:
    """Get diff of staged changes"""
    try:
        # Get list of staged files
        files_out, _, _ = run_git_command(["git", "diff", "--cached", "--name-only"])
        files = [f.strip() for f in files_out.split("\n") if f.strip()]

        if not files:
            return None

        # Get actual diff
        diff_out, _, _ = run_git_command(["git", "diff", "--cached"])

        return GitDiff(diff=diff_out, staged=True, files=files)
    except Exception as e:
        print(f"❌ Error getting staged diff: {e}")
        return None


def get_unstaged_diff() -> Optional[GitDiff]:
    """Get diff of unstaged changes"""
    try:
        diff_out, _, _ = run_git_command(["git", "diff"])

        if not diff_out.strip():
            return None

        return GitDiff(diff=diff_out, staged=False, files=[])
    except Exception as e:
        print(f"❌ Error getting unstaged diff: {e}")
        return None


def stage_all_changes() -> bool:
    """Stage all changes"""
    try:
        _, stderr, code = run_git_command(["git", "add", "-A"])
        return code == 0
    except Exception as e:
        print(f"❌ Error staging changes: {e}")
        return False


def commit_with_message(message: str) -> bool:
    """Commit with the given message"""
    temp_file = None
    try:
        # Create temporary file for multi-line commit messages with UTF-8 encoding
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", encoding="utf-8"
        ) as f:
            f.write(message)
            temp_file = f.name

        _, stderr, code = run_git_command(["git", "commit", "-F", temp_file])
        return code == 0
    except Exception as e:
        print(f"❌ Commit failed: {e}")
        return False
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass


def get_repository_root() -> Optional[str]:
    """Get the root directory of the git repository"""
    try:
        stdout, _, code = run_git_command(["git", "rev-parse", "--show-toplevel"])
        if code == 0:
            return stdout.strip()
        return None
    except Exception:
        return None
