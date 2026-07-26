import datetime
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class GitDiff:
    diff: str
    staged: bool
    files: List[str]


class GitService:
    def __init__(self, diff: str, staged: bool, files: List[str]):
        self.diff = diff
        self.staged = staged
        self.files = files

    @staticmethod
    def get_repo_info(repo_path: str) -> Dict:
        """Get information about the repository"""

        info = {
            "name": os.path.basename(repo_path),
            "description": "",
            "primary_language": "Unknown",
            "languages": [],
            "top_files": [],
            "has_license": False,
            "has_contributing": False,
        }

        try:
            stdout, _, _ = GitService.run_git_command(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=repo_path,
            )
            if stdout.strip():
                remote_url = stdout.strip()
                if "github.com" in remote_url:
                    parts = remote_url.replace(".git", "").split("/")
                    if len(parts) >= 2:
                        info["name"] = parts[-1]

            readme_path = Path(repo_path) / "README.md"
            if readme_path.exists():
                try:
                    with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        for line in content.split("\n")[:10]:
                            if line.strip() and not line.startswith("#") and len(line) < 200:
                                info["description"] = line.strip()
                                break
                except Exception:
                    pass

            languages = set()
            for root, dirs, files in os.walk(repo_path):
                if ".git" in dirs:
                    dirs.remove(".git")

                skip_dirs = [
                    "__pycache__",
                    "node_modules",
                    "venv",
                    "env",
                    ".venv",
                    "dist",
                    "build",
                    ".idea",
                    ".vscode",
                ]
                for skip in skip_dirs:
                    if skip in dirs:
                        dirs.remove(skip)

                for file in files[:50]:
                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        lang = GitService.get_language_from_extension(ext)
                        if lang:
                            languages.add(lang)

            info["languages"] = list(languages)
            if languages:
                info["primary_language"] = list(languages)[0]

            top_files = []
            for root, dirs, files in os.walk(repo_path):
                if ".git" in dirs:
                    dirs.remove(".git")

                skip_dirs = [
                    "__pycache__",
                    "node_modules",
                    "venv",
                    "env",
                    ".venv",
                    "dist",
                    "build",
                ]
                for skip in skip_dirs:
                    if skip in dirs:
                        dirs.remove(skip)

                for file in files[:20]:
                    if not file.startswith(".") and file not in ["README.md", "LICENSE", ".gitignore"]:
                        rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                        if not rel_path.startswith("."):
                            top_files.append(rel_path)

            info["top_files"] = top_files[:15]

            try:
                files_list = os.listdir(repo_path)
                info["has_license"] = any(
                    f.lower() in ["license", "license.txt", "license.md", "licence"]
                    for f in files_list
                )
                info["has_contributing"] = any(
                    f.lower().startswith("contributing") for f in files_list
                )
            except Exception:
                pass

        except Exception as e:
            print(f"⚠️  Error getting repo info: {e}")

        return info

    @staticmethod
    def get_language_from_extension(ext: str) -> str:
        """Map file extension to language name"""
        lang_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React",
            ".tsx": "React TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".h": "C/C++",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".html": "HTML",
            ".htm": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".sass": "SASS",
            ".less": "LESS",
            ".json": "JSON",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".xml": "XML",
            ".md": "Markdown",
            ".txt": "Text",
            ".sh": "Bash/Shell",
            ".bash": "Bash",
            ".bat": "Batch",
            ".ps1": "PowerShell",
            ".sql": "SQL",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".kts": "Kotlin Script",
            ".dart": "Dart",
            ".r": "R",
            ".m": "Objective-C",
            ".mm": "Objective-C++",
        }
        return lang_map.get(ext, "")

    @staticmethod
    def change_directory(path: str) -> bool:
        """Change to specified directory"""
        try:
            os.chdir(path)
            return True
        except Exception as e:
            print(f"❌ Failed to change directory: {e}")
            return False

    @staticmethod
    def get_current_directory() -> str:
        """Get current working directory"""
        return os.getcwd()

    @staticmethod
    def run_git_command(cmd: List[str], cwd: Optional[str] = None) -> Tuple[str, str, int]:
        """Run a git command and return output with UTF-8 encoding."""
        try:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
            stdout, stderr = process.communicate()
            return stdout, stderr, process.returncode
        except Exception as e:
            return "", str(e), 1

    @staticmethod
    def get_staged_diff(repo_path: str) -> Optional[GitDiff]:
        """Get diff of staged changes"""
        try:
            files_out, _, _ = GitService.run_git_command(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo_path,
            )
            files = [f.strip() for f in files_out.split("\n") if f.strip()]

            if not files:
                return None

            diff_out, _, _ = GitService.run_git_command(["git", "diff", "--cached"], cwd=repo_path)
            return GitDiff(diff=diff_out, staged=True, files=files)
        except Exception as e:
            print(f"❌ Error getting staged diff: {e}")
            return None

    @staticmethod
    def get_unstaged_diff(repo_path: Optional[str] = None) -> Optional[GitDiff]:
        """Get diff of unstaged changes"""
        try:
            diff_out, _, _ = GitService.run_git_command(["git", "diff"], cwd=repo_path)
            if not diff_out.strip():
                return None
            return GitDiff(diff=diff_out, staged=False, files=[])
        except Exception as e:
            print(f"❌ Error getting unstaged diff: {e}")
            return None

    @staticmethod
    def stage_all_changes(repo_path: Optional[str] = None) -> bool:
        """Stage all changes"""
        try:
            _, _, code = GitService.run_git_command(["git", "add", "-A"], cwd=repo_path)
            return code == 0
        except Exception as e:
            print(f"❌ Error staging changes: {e}")
            return False

    @staticmethod
    def commit_with_message(message: str, repo_path: str, commit_datetime: Optional[str] = None) -> bool:
        """Commit with the given message"""
        temp_file = None
        try:
            if commit_datetime is not None:
                # Set the GIT_AUTHOR_DATE environment variable
                os.environ["GIT_AUTHOR_DATE"] = commit_datetime
                # Set the GIT_COMMITTER_DATE environment variable
                os.environ["GIT_COMMITTER_DATE"] = commit_datetime

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt", encoding="utf-8"
            ) as f:
                f.write(message)
                temp_file = f.name

            _, _, code = GitService.run_git_command(["git", "commit", "-F", temp_file], cwd=repo_path)

            # Clear the environment variables
            if commit_datetime is not None:
                del os.environ["GIT_AUTHOR_DATE"]
                del os.environ["GIT_COMMITTER_DATE"]

            return True
        except Exception as e:
            print(f"❌ Commit failed: {e}")
            return False
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

    @staticmethod
    def get_repository_root(repo_path: Optional[str] = None) -> Optional[str]:
        """Get the root directory of the git repository."""
        try:
            stdout, _, code = GitService.run_git_command(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=repo_path,
            )
            if code == 0:
                return stdout.strip()
            return None
        except Exception:
            return None


    @staticmethod
    def get_current_branch(repo_path: Optional[str] = None) -> str:
        """Get the current active branch name."""
        try:
            stdout, _, code = GitService.run_git_command(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
            )
            if code == 0 and stdout.strip():
                return stdout.strip()
            # Fallback for older git versions or detached HEAD
            stdout, _, code = GitService.run_git_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
            )
            if code == 0 and stdout.strip():
                return stdout.strip()
            return "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def unstage_all_changes(repo_path: Optional[str] = None) -> bool:
        """Reset staged changes (unstage all)"""
        try:
            _, _, code = GitService.run_git_command(["git", "reset"], cwd=repo_path)
            return code == 0
        except Exception:
            return False

    @staticmethod
    def get_repo_status_summary(repo_path: Optional[str] = None) -> Dict:
        """Get summary of repository git status including staged, unstaged, and branch."""
        summary = {
            "is_repo": False,
            "branch": "unknown",
            "staged_files": [],
            "unstaged_files": [],
            "untracked_files": [],
        }
        if not repo_path:
            return summary

        root = GitService.get_repository_root(repo_path)
        if not root:
            return summary

        summary["is_repo"] = True
        summary["branch"] = GitService.get_current_branch(root)

        # Staged files
        stdout, _, _ = GitService.run_git_command(
            ["git", "diff", "--cached", "--name-status"],
            cwd=root,
        )
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                parts = line.split(maxsplit=1)
                status = parts[0] if len(parts) > 0 else "M"
                filename = parts[1] if len(parts) > 1 else line
                summary["staged_files"].append({"status": status, "file": filename})

        # Unstaged modified files
        stdout, _, _ = GitService.run_git_command(
            ["git", "diff", "--name-status"],
            cwd=root,
        )
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                parts = line.split(maxsplit=1)
                status = parts[0] if len(parts) > 0 else "M"
                filename = parts[1] if len(parts) > 1 else line
                summary["unstaged_files"].append({"status": status, "file": filename})

        # Untracked files
        stdout, _, _ = GitService.run_git_command(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=root,
        )
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                summary["untracked_files"].append(line)

        # Unpushed count
        summary["unpushed_count"] = GitService.get_unpushed_commits_count(root)

        return summary

    @staticmethod
    def get_unpushed_commits_count(repo_path: Optional[str] = None) -> int:
        """Get the number of unpushed commits on current branch."""
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return 0
            stdout, _, code = GitService.run_git_command(
                ["git", "rev-list", "@{u}..HEAD", "--count"],
                cwd=root,
            )
            if code == 0 and stdout.strip().isdigit():
                return int(stdout.strip())
            return 0
        except Exception:
            return 0

    @staticmethod
    def push_commits(repo_path: Optional[str] = None, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
        """Push commits to the remote repository. Returns (success, message)."""
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return False, "Not a valid git repository."

            curr_branch = GitService.get_current_branch(root)
            cmd = ["git", "push"]
            if remote and branch:
                cmd.extend([remote, branch])
            elif remote and curr_branch and curr_branch != "unknown":
                cmd.extend(["-u", remote, curr_branch])

            stdout, stderr, code = GitService.run_git_command(cmd, cwd=root)
            if code == 0:
                msg = stdout.strip() or stderr.strip() or "Pushed to remote successfully."
                return True, msg
            else:
                err = stderr.strip() or stdout.strip() or "Push failed."
                return False, err
        except Exception as e:
            return False, str(e)

    @staticmethod
    def pull_commits(repo_path: Optional[str] = None, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
        """Pull latest changes from the remote repository."""
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return False, "Not a valid git repository."

            curr_branch = GitService.get_current_branch(root)
            cmd = ["git", "pull"]
            if remote and branch:
                cmd.extend([remote, branch])
            elif remote and curr_branch and curr_branch != "unknown":
                cmd.extend([remote, curr_branch])

            stdout, stderr, code = GitService.run_git_command(cmd, cwd=root)
            if code == 0:
                msg = stdout.strip() or stderr.strip() or "Already up to date."
                return True, msg
            else:
                err = stderr.strip() or stdout.strip() or "Pull failed."
                return False, err
        except Exception as e:
            return False, str(e)

    @staticmethod
    def stage_single_file(file_path: str, repo_path: Optional[str] = None) -> bool:
        """Stage a single file."""
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return False
            _, _, code = GitService.run_git_command(["git", "add", "--", file_path], cwd=root)
            return code == 0
        except Exception:
            return False

    @staticmethod
    def unstage_single_file(file_path: str, repo_path: Optional[str] = None) -> bool:
        """Unstage a single file."""
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return False
            _, _, code = GitService.run_git_command(["git", "restore", "--staged", "--", file_path], cwd=root)
            if code != 0:
                _, _, code = GitService.run_git_command(["git", "reset", "HEAD", "--", file_path], cwd=root)
            return code == 0
        except Exception:
            return False

    @staticmethod
    def get_file_diff(file_path: str, repo_path: Optional[str] = None, staged_only: bool = False) -> str:
        """Get diff for a specific single file."""
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return ""
            if staged_only:
                stdout, _, _ = GitService.run_git_command(["git", "diff", "--cached", "--", file_path], cwd=root)
            else:
                stdout, _, _ = GitService.run_git_command(["git", "diff", "HEAD", "--", file_path], cwd=root)
                if not stdout.strip():
                    stdout, _, _ = GitService.run_git_command(["git", "diff", "--", file_path], cwd=root)
            return stdout
        except Exception:
            return ""

    @staticmethod
    def get_detailed_file_status(repo_path: Optional[str] = None) -> List[Dict]:
        """Get status of all changed and untracked files with staging state."""
        results = []
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return results

            stdout, _, code = GitService.run_git_command(["git", "status", "--porcelain", "-uall"], cwd=root)
            if code != 0:
                return results

            for line in stdout.splitlines():
                if len(line) >= 4:
                    index_status = line[0]
                    work_status = line[1]
                    filename = line[3:].strip()
                    if " -> " in filename:
                        filename = filename.split(" -> ")[-1].strip()

                    is_staged = index_status not in (" ", "?", "!")
                    
                    status_type = "Modified"
                    if index_status == "A" or work_status == "A" or index_status == "?" or work_status == "?":
                        status_type = "Untracked" if index_status == "?" else "Added"
                    elif index_status == "D" or work_status == "D":
                        status_type = "Deleted"
                    elif index_status == "R" or work_status == "R":
                        status_type = "Renamed"

                    results.append({
                        "file": filename,
                        "staged": is_staged,
                        "index_status": index_status,
                        "work_status": work_status,
                        "status_type": status_type,
                    })
        except Exception:
            pass
        return results



def get_repo_info(repo_path: str) -> Dict:
    return GitService.get_repo_info(repo_path)


def get_language_from_extension(ext: str) -> str:
    return GitService.get_language_from_extension(ext)


def change_directory(path: str) -> bool:
    return GitService.change_directory(path)


def get_current_directory() -> str:
    return GitService.get_current_directory()


def run_git_command(cmd: List[str], cwd: Optional[str] = None) -> Tuple[str, str, int]:
    return GitService.run_git_command(cmd, cwd=cwd)


def get_staged_diff(repo_path: str) -> Optional[GitDiff]:
    return GitService.get_staged_diff(repo_path)


def get_unstaged_diff(repo_path: Optional[str] = None) -> Optional[GitDiff]:
    return GitService.get_unstaged_diff(repo_path)


def stage_all_changes(repo_path: Optional[str] = None) -> bool:
    return GitService.stage_all_changes(repo_path)


def unstage_all_changes(repo_path: Optional[str] = None) -> bool:
    return GitService.unstage_all_changes(repo_path)


def pull_commits(repo_path: Optional[str] = None, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
    return GitService.pull_commits(repo_path, remote, branch)


def stage_single_file(file_path: str, repo_path: Optional[str] = None) -> bool:
    return GitService.stage_single_file(file_path, repo_path)


def unstage_single_file(file_path: str, repo_path: Optional[str] = None) -> bool:
    return GitService.unstage_single_file(file_path, repo_path)


def get_file_diff(file_path: str, repo_path: Optional[str] = None, staged_only: bool = False) -> str:
    return GitService.get_file_diff(file_path, repo_path, staged_only)


def get_detailed_file_status(repo_path: Optional[str] = None) -> List[Dict]:
    return GitService.get_detailed_file_status(repo_path)


def get_repository_root(repo_path: Optional[str] = None) -> Optional[str]:
    return GitService.get_repository_root(repo_path)


def get_current_branch(repo_path: Optional[str] = None) -> str:
    return GitService.get_current_branch(repo_path)


def get_repo_status_summary(repo_path: Optional[str] = None) -> Dict:
    return GitService.get_repo_status_summary(repo_path)




