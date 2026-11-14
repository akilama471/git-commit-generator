from pathlib import Path
from typing import Optional

from core.config.config_manager import ConfigManager
from core.services.ai_service import GeminiClient
from core.services.git_service import GitService


class CommitService:
    def __init__(self, commit_generator):
        self.commit_generator = commit_generator

    @staticmethod
    def generate_commit_message(path: str, model: Optional[str] = None, auto_stage: bool = False):
        """Generate a commit message string for staged changes."""
        success, result = CommitService.generate_commit_options(
            path, model=model, auto_stage=auto_stage
        )
        if not success:
            return str(result)
        if isinstance(result, list) and result:
            return result[0]
        return "Failed to generate commit messages"

    @staticmethod
    def generate_commit_options(
        path: str, model: Optional[str] = None, auto_stage: bool = False
    ):
        """Generate commit message options for staged changes.

        Returns: (success: bool, result: list[str] | str)
        """
        if not path:
            return False, "Please select a project folder."

        target_path = str(Path(path).resolve())
        git_diff = GitService.get_staged_diff(target_path)

        if (not git_diff or not git_diff.diff) and auto_stage:
            if GitService.stage_all_changes(target_path):
                git_diff = GitService.get_staged_diff(target_path)

        if not git_diff or not git_diff.diff:
            return False, "No staged changes found! Stage changes or click '+ Stage All' first."

        status_code, config = ConfigManager.get_config()
        if status_code != 200:
            return False, f"Error {status_code}: {config}"

        use_model = model or config.get("model", "gemini-2.0-flash-lite")
        client = GeminiClient(
            api_key=config.get("api_key", ""),
            model=use_model,
            max_diff_len=config.get("max_diff_length", 5000),
            temperature=config.get("temperature", 0.7),
        )

        return client.generate_commit_messages_safe(git_diff.diff, files=git_diff.files)