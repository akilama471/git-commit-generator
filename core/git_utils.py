import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple  # Add Dict here


class GitDiff:
    def __init__(self, diff: str, staged: bool, files: List[str]):
        self.diff = diff
        self.staged = staged
        self.files = files


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
        # Try to get git remote info
        stdout, _, _ = run_git_command(["git", "config", "--get", "remote.origin.url"])
        if stdout.strip():
            remote_url = stdout.strip()
            # Extract repo name from URL
            if "github.com" in remote_url:
                parts = remote_url.replace(".git", "").split("/")
                if len(parts) >= 2:
                    info["name"] = parts[-1]

        # Check for existing README
        readme_path = Path(repo_path) / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    # Try to extract first line as description
                    lines = content.split("\n")
                    for line in lines[:10]:
                        if (
                            line.strip()
                            and not line.startswith("#")
                            and len(line) < 200
                        ):
                            info["description"] = line.strip()
                            break
            except:
                pass

        # Detect languages by scanning files
        languages = set()
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in dirs:
                dirs.remove(".git")

            # Skip common directories
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

            for file in files[:50]:  # Limit scanning
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    lang = get_language_from_extension(ext)
                    if lang:
                        languages.add(lang)

        info["languages"] = list(languages)
        if languages:
            # Simple heuristic for primary language (most common in root)
            info["primary_language"] = list(languages)[0]

        # Get top files
        top_files = []
        for root, dirs, files in os.walk(repo_path):
            if ".git" in dirs:
                dirs.remove(".git")
            # Skip common directories
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
                if not file.startswith(".") and file not in [
                    "README.md",
                    "LICENSE",
                    ".gitignore",
                ]:
                    rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                    if not rel_path.startswith("."):
                        top_files.append(rel_path)

        info["top_files"] = top_files[:15]

        # Check for important files
        try:
            files_list = os.listdir(repo_path)
            info["has_license"] = any(
                f.lower() in ["license", "license.txt", "license.md", "licence"]
                for f in files_list
            )
            info["has_contributing"] = any(
                f.lower().startswith("contributing") for f in files_list
            )
        except:
            pass

    except Exception as e:
        print(f"⚠️  Error getting repo info: {e}")

    return info


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


def change_directory(path: str) -> bool:
    """Change to specified directory"""
    try:
        os.chdir(path)
        return True
    except Exception as e:
        print(f"❌ Failed to change directory: {e}")
        return False


def get_current_directory() -> str:
    """Get current working directory"""
    return os.getcwd()


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
