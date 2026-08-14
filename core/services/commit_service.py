import os
import sys
from pathlib import Path
from typing import Optional

from core.services.git_service import GitService
from core.config.config_manager import ConfigManager
from core.services.ai_service import GeminiClient


class CommitService:
    def __init__(self, commit_generator):
        self.commit_generator = commit_generator

    @staticmethod
    def generate_commit_message(path: str, model: Optional[str]):
        """Generate commit message for staged changes

        PATH can be:
        - Current directory: .
        - Relative path: ./my-project
        - Absolute path: M:/Projects/my-project
        """

        if not path:
            return "Please select a project folder."

        target_path = Path(path).resolve()

        # Get staged diff
        git_diff = GitService.get_staged_diff(str(target_path))

        if not git_diff or not git_diff.diff:
            return "No staged changes found! Use --add to stage all changes or run 'git add' first"

        # Load config
        status_code, config = ConfigManager.get_config()

        if status_code != 200:
            return f"Error {status_code}: {config}"

        # Initialize AI client
        use_model = model or config.get("model", "gemini-2.0-flash-lite")
        client = GeminiClient(
            api_key=config["api_key"],
            model=use_model,
            max_diff_len=config["max_diff_length"],
            temperature=config.get("temperature", 0.7),
        )

        # Generate messages
        options = client.generate_commit_messages(git_diff.diff)

        if not options:
            return "Failed to generate commit messages"

        return options[0]