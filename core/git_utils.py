import subprocess
import os
import tempfile
from typing import List, Optional, Tuple

class GitDiff:
    def __init__(self, diff: str, staged: bool, files: List[str]):
        self.diff = diff
        self.staged = staged
        self.files = files

def run_git_command(cmd: List[str]) -> Tuple[str, str, int]:
    """Run a git command and return output"""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True
    )
    stdout, stderr = process.communicate()
    return stdout, stderr, process.returncode

def get_staged_diff() -> Optional[GitDiff]:
    """Get diff of staged changes"""
    # Get list of staged files
    files_out, _, _ = run_git_command(['git', 'diff', '--cached', '--name-only'])
    files = [f.strip() for f in files_out.split('\n') if f.strip()]
    
    if not files:
        return None
    
    # Get actual diff
    diff_out, _, _ = run_git_command(['git', 'diff', '--cached'])
    
    return GitDiff(diff=diff_out, staged=True, files=files)

def get_unstaged_diff() -> Optional[GitDiff]:
    """Get diff of unstaged changes"""
    diff_out, _, _ = run_git_command(['git', 'diff'])
    
    if not diff_out.strip():
        return None
    
    return GitDiff(diff=diff_out, staged=False, files=[])

def stage_all_changes():
    """Stage all changes"""
    _, stderr, code = run_git_command(['git', 'add', '-A'])
    return code == 0

def commit_with_message(message: str) -> bool:
    """Commit with the given message"""
    # Create temporary file for multi-line commit messages
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(message)
        temp_file = f.name
    
    try:
        _, stderr, code = run_git_command(['git', 'commit', '-F', temp_file])
        os.unlink(temp_file)
        return code == 0
    except Exception as e:
        os.unlink(temp_file)
        print(f"❌ Commit failed: {e}")
        return False

def get_repository_root() -> Optional[str]:
    """Get the root directory of the git repository"""
    stdout, _, code = run_git_command(['git', 'rev-parse', '--show-toplevel'])
    if code == 0:
        return stdout.strip()
    return None