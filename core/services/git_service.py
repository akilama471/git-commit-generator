import datetime
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


LOCK_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "poetry.lock",
    "composer.lock",
    "Gemfile.lock",
}


@dataclass
class GitDiff:
    diff: str
    staged: bool
    files: List[str]


class GitService:
    _root_cache: Dict[str, str] = {}

    def __init__(self, diff: str, staged: bool, files: List[str]):
        self.diff = diff
        self.staged = staged
        self.files = files

    @staticmethod
    def get_repo_info(repo_path: str) -> Dict:
        """Get information about the repository in a single bounded walk."""

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
                        content = f.read(4096)
                        for line in content.split("\n")[:10]:
                            if line.strip() and not line.startswith("#") and len(line) < 200:
                                info["description"] = line.strip()
                                break
                except Exception:
                    pass

            skip_dirs = {
                ".git",
                "__pycache__",
                "node_modules",
                "venv",
                "env",
                ".venv",
                "dist",
                "build",
                ".idea",
                ".vscode",
            }
            languages = set()
            top_files = []
            inspected_files = 0
            max_files = 100
            max_depth = 3

            for root, dirs, files in os.walk(repo_path):
                rel_root = os.path.relpath(root, repo_path)
                depth = 0 if rel_root == "." else len(rel_root.split(os.sep))
                if depth >= max_depth:
                    dirs[:] = []
                else:
                    dirs[:] = [d for d in dirs if d not in skip_dirs]

                if depth == 0:
                    info["has_license"] = any(
                        f.lower() in ("license", "license.txt", "license.md", "licence")
                        for f in files
                    )
                    info["has_contributing"] = any(
                        f.lower().startswith("contributing") for f in files
                    )

                for file in files:
                    if inspected_files >= max_files:
                        break
                    inspected_files += 1

                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        lang = GitService.get_language_from_extension(ext)
                        if lang:
                            languages.add(lang)

                    if (
                        len(top_files) < 15
                        and not file.startswith(".")
                        and file not in ("README.md", "LICENSE", ".gitignore")
                    ):
                        rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                        if not rel_path.startswith("."):
                            top_files.append(rel_path)

                if inspected_files >= max_files:
                    break

            info["languages"] = list(languages)
            if languages:
                info["primary_language"] = info["languages"][0]
            info["top_files"] = top_files[:15]

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
    def run_git_command(
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: int = 15,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, str, int]:
        """Run a git command non-interactively with timeout and UTF-8 encoding."""
        process = None
        try:
            proc_env = os.environ.copy()
            proc_env["GIT_TERMINAL_PROMPT"] = "0"
            proc_env["GCM_INTERACTIVE"] = "never"
            if env:
                proc_env.update(env)

            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                env=proc_env,
                creationflags=creationflags,
            )
            stdout, stderr = process.communicate(timeout=timeout)
            return stdout, stderr, process.returncode
        except subprocess.TimeoutExpired:
            if process is not None:
                try:
                    process.kill()
                    process.communicate()
                except Exception:
                    pass
            return "", f"Git command timed out after {timeout}s.", 124
        except Exception as e:
            return "", str(e), 1

    @staticmethod
    def get_staged_diff(repo_path: Optional[str] = None) -> Optional[GitDiff]:
        """Get diff of staged changes with stat summary and lockfile noise filtering."""
        try:
            files_out, _, code = GitService.run_git_command(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo_path,
            )
            if code != 0:
                return None

            files = [f.strip() for f in files_out.splitlines() if f.strip()]
            if not files:
                return None

            stat_out, _, _ = GitService.run_git_command(
                ["git", "diff", "--cached", "--stat"],
                cwd=repo_path,
            )

            non_lock_files = [f for f in files if os.path.basename(f) not in LOCK_FILES]
            diff_cmd = ["git", "diff", "--cached"]
            if non_lock_files and len(non_lock_files) < len(files) and len(non_lock_files) <= 100:
                diff_cmd.append("--")
                diff_cmd.extend(non_lock_files)

            diff_out, _, _ = GitService.run_git_command(diff_cmd, cwd=repo_path)
            if stat_out.strip():
                combined = f"Stat summary:\n{stat_out.strip()}\n\n{diff_out}"
            else:
                combined = diff_out
            return GitDiff(diff=combined, staged=True, files=files)
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
            _, _, code = GitService.run_git_command(["git", "add", "-A"], cwd=repo_path, timeout=30)
            return code == 0
        except Exception as e:
            print(f"❌ Error staging changes: {e}")
            return False

    @staticmethod
    def commit_with_message_detailed(
        message: str, repo_path: Optional[str] = None, commit_datetime: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Commit with the given message and return (success, details)."""
        temp_file = None
        try:
            extra_env = None
            if commit_datetime is not None:
                extra_env = {
                    "GIT_AUTHOR_DATE": commit_datetime,
                    "GIT_COMMITTER_DATE": commit_datetime,
                }

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".txt", encoding="utf-8"
            ) as f:
                f.write(message)
                temp_file = f.name

            stdout, stderr, code = GitService.run_git_command(
                ["git", "commit", "-F", temp_file],
                cwd=repo_path,
                timeout=30,
                env=extra_env,
            )

            if code == 0:
                return True, stdout.strip() or "Commit created successfully."
            err = stderr.strip() or stdout.strip() or "Git commit failed."
            return False, err
        except Exception as e:
            return False, str(e)
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

    @staticmethod
    def commit_with_message(
        message: str, repo_path: Optional[str] = None, commit_datetime: Optional[str] = None
    ) -> bool:
        """Commit with the given message."""
        success, err = GitService.commit_with_message_detailed(message, repo_path, commit_datetime)
        if not success:
            print(f"❌ Commit failed: {err}")
        return success

    @staticmethod
    def get_repository_root(repo_path: Optional[str] = None) -> Optional[str]:
        """Get the root directory of the git repository (cached)."""
        try:
            key = str(Path(repo_path or os.getcwd()).resolve())
            cached = GitService._root_cache.get(key)
            if cached and os.path.exists(os.path.join(cached, ".git")):
                return cached

            stdout, _, code = GitService.run_git_command(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=repo_path,
            )
            if code == 0 and stdout.strip():
                root = stdout.strip()
                GitService._root_cache[key] = root
                return root
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
    def _parse_porcelain_branch_line(header: str) -> Tuple[str, int]:
        """Extract (branch_name, unpushed_count) from a `git status --porcelain=v1 -b` header line."""
        branch = "unknown"
        unpushed = 0
        if not header.startswith("## "):
            return branch, unpushed

        info = header[3:].strip()
        if info.startswith("No commits yet on "):
            branch = info[len("No commits yet on "):].strip()
        elif info.startswith("Initial commit on "):
            branch = info[len("Initial commit on "):].strip()
        elif info.startswith("HEAD"):
            branch = "HEAD (detached)"
        else:
            branch = info.split("...")[0].split(" [")[0].strip() or "unknown"

        ahead_match = re.search(r"\[[^\]]*ahead (\d+)", info)
        if ahead_match:
            unpushed = int(ahead_match.group(1))
        return branch, unpushed

    @staticmethod
    def _parse_porcelain_entry(line: str) -> Optional[Dict]:
        """Parse one entry line from `git status --porcelain=v1`."""
        if len(line) < 4:
            return None
        index_status = line[0]
        work_status = line[1]
        filename = line[3:].rstrip("\r\n")
        if " -> " in filename:
            filename = filename.split(" -> ")[-1]
        if filename.startswith('"') and filename.endswith('"') and len(filename) >= 2:
            filename = filename[1:-1]

        is_staged = index_status not in (" ", "?", "!")
        status_type = "Modified"
        if index_status == "?" or work_status == "?":
            status_type = "Untracked"
        elif index_status == "A" or work_status == "A":
            status_type = "Added"
        elif index_status == "D" or work_status == "D":
            status_type = "Deleted"
        elif index_status == "R" or work_status == "R":
            status_type = "Renamed"

        return {
            "file": filename,
            "staged": is_staged,
            "index_status": index_status,
            "work_status": work_status,
            "status_type": status_type,
        }

    @staticmethod
    def get_repo_status_summary(repo_path: Optional[str] = None) -> Dict:
        """Get repository git status summary in a single git invocation."""
        summary = {
            "is_repo": False,
            "branch": "unknown",
            "staged_files": [],
            "unstaged_files": [],
            "untracked_files": [],
            "unpushed_count": 0,
            "error": "",
        }
        if not repo_path:
            return summary

        if not os.path.isdir(repo_path):
            summary["error"] = "Folder does not exist"
            return summary

        root = GitService.get_repository_root(repo_path)
        if not root:
            _, stderr, _ = GitService.run_git_command(
                ["git", "rev-parse", "--show-toplevel"], cwd=repo_path
            )
            if "dubious ownership" in stderr.lower():
                summary["error"] = "Git dubious ownership (safe.directory required)"
            else:
                summary["error"] = "Not a valid Git repository"
            return summary

        summary["is_repo"] = True

        stdout, _, code = GitService.run_git_command(
            ["git", "status", "--porcelain=v1", "-b", "-u"],
            cwd=root,
        )
        if code != 0:
            stdout, _, code = GitService.run_git_command(
                ["git", "status", "--porcelain", "-b"],
                cwd=root,
            )
            if code != 0:
                summary["branch"] = GitService.get_current_branch(root)
                return summary

        lines = stdout.splitlines()
        if lines and lines[0].startswith("## "):
            branch, unpushed = GitService._parse_porcelain_branch_line(lines[0])
            summary["branch"] = branch
            summary["unpushed_count"] = unpushed
            entry_lines = lines[1:]
        else:
            summary["branch"] = GitService.get_current_branch(root)
            entry_lines = lines

        for line in entry_lines:
            parsed = GitService._parse_porcelain_entry(line)
            if not parsed:
                continue
            x = parsed["index_status"]
            y = parsed["work_status"]
            filename = parsed["file"]

            if x == "?" and y == "?":
                summary["untracked_files"].append(filename)
            elif x == "!" and y == "!":
                continue
            else:
                if x != " ":
                    summary["staged_files"].append({"status": x, "file": filename})
                if y != " ":
                    summary["unstaged_files"].append({"status": y, "file": filename})

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
    def push_commits(
        repo_path: Optional[str] = None, remote: str = "origin", branch: Optional[str] = None
    ) -> Tuple[bool, str]:
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

            stdout, stderr, code = GitService.run_git_command(cmd, cwd=root, timeout=60)
            if code == 0:
                msg = stdout.strip() or stderr.strip() or "Pushed to remote successfully."
                return True, msg
            err = stderr.strip() or stdout.strip() or "Push failed."
            return False, err
        except Exception as e:
            return False, str(e)

    @staticmethod
    def pull_commits(
        repo_path: Optional[str] = None, remote: str = "origin", branch: Optional[str] = None
    ) -> Tuple[bool, str]:
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

            stdout, stderr, code = GitService.run_git_command(cmd, cwd=root, timeout=60)
            if code == 0:
                msg = stdout.strip() or stderr.strip() or "Already up to date."
                return True, msg
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
            _, _, code = GitService.run_git_command(
                ["git", "restore", "--staged", "--", file_path], cwd=root
            )
            if code != 0:
                _, _, code = GitService.run_git_command(
                    ["git", "reset", "HEAD", "--", file_path], cwd=root
                )
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
                stdout, _, _ = GitService.run_git_command(
                    ["git", "diff", "--cached", "--", file_path], cwd=root
                )
            else:
                stdout, _, _ = GitService.run_git_command(
                    ["git", "diff", "HEAD", "--", file_path], cwd=root
                )
                if not stdout.strip():
                    stdout, _, _ = GitService.run_git_command(
                        ["git", "diff", "--", file_path], cwd=root
                    )
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

            stdout, _, code = GitService.run_git_command(
                ["git", "status", "--porcelain=v1", "-u"], cwd=root
            )
            if code != 0:
                stdout, _, code = GitService.run_git_command(
                    ["git", "status", "--porcelain"], cwd=root
                )
            if code != 0:
                return results

            for line in stdout.splitlines():
                parsed = GitService._parse_porcelain_entry(line)
                if parsed:
                    results.append(parsed)
        except Exception:
            pass
        return results

    @staticmethod
    def scan_for_repositories(parent_path: str, max_depth: int = 3) -> List[str]:
        """Discover Git repositories under parent_path up to max_depth levels."""
        found: List[str] = []
        seen = set()
        if not parent_path or not os.path.isdir(parent_path):
            return found

        skip_dirs = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "env",
            "__pycache__",
            "dist",
            "build",
            ".idea",
            ".vscode",
        }
        base_path = os.path.abspath(parent_path)

        try:
            for root, dirs, files in os.walk(base_path):
                if ".git" in dirs or ".git" in files:
                    resolved = str(Path(root).resolve())
                    key = os.path.normcase(resolved)
                    if key not in seen:
                        seen.add(key)
                        found.append(resolved)
                    dirs[:] = []
                    continue

                rel = os.path.relpath(root, base_path)
                depth = 0 if rel == "." else len(rel.split(os.sep))
                if depth >= max_depth:
                    dirs[:] = []
                else:
                    dirs[:] = [d for d in dirs if d not in skip_dirs]
        except Exception:
            pass

        return sorted(found, key=lambda p: (os.path.basename(p).lower(), p.lower()))

    @staticmethod
    def get_local_branches(repo_path: Optional[str] = None) -> List[str]:
        """Return list of local branch names for the repository."""
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return []
            stdout, _, code = GitService.run_git_command(
                ["git", "branch", "--format=%(refname:short)"],
                cwd=root,
            )
            if code != 0:
                return []
            return [line.strip() for line in stdout.splitlines() if line.strip()]
        except Exception:
            return []

    @staticmethod
    def checkout_branch(repo_path: str, branch_name: str) -> Tuple[bool, str]:
        """Switch to the specified local branch."""
        try:
            root = GitService.get_repository_root(repo_path)
            if not root:
                return False, "Not a valid git repository."
            stdout, stderr, code = GitService.run_git_command(
                ["git", "checkout", branch_name],
                cwd=root,
                timeout=30,
            )
            msg = (stderr or stdout or "").strip()
            if code == 0:
                return True, msg or f"Switched to branch '{branch_name}'."
            return False, msg or f"Failed to switch to branch '{branch_name}'."
        except Exception as e:
            return False, str(e)


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


def get_staged_diff(repo_path: Optional[str] = None) -> Optional[GitDiff]:
    return GitService.get_staged_diff(repo_path)


def get_unstaged_diff(repo_path: Optional[str] = None) -> Optional[GitDiff]:
    return GitService.get_unstaged_diff(repo_path)


def stage_all_changes(repo_path: Optional[str] = None) -> bool:
    return GitService.stage_all_changes(repo_path)


def unstage_all_changes(repo_path: Optional[str] = None) -> bool:
    return GitService.unstage_all_changes(repo_path)


def commit_with_message(
    message: str, repo_path: Optional[str] = None, commit_datetime: Optional[str] = None
) -> bool:
    return GitService.commit_with_message(message, repo_path, commit_datetime)


def pull_commits(
    repo_path: Optional[str] = None, remote: str = "origin", branch: Optional[str] = None
) -> Tuple[bool, str]:
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




