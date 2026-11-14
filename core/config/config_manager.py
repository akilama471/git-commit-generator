import os
import threading
from pathlib import Path
from typing import List
import yaml

CONFIG_DIR = Path.home() / ".git-commit-ai"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG = {
    "api_key": "your-api-key-here",
    "model": "gemini-2.0-flash-lite",
    "max_diff_length": 5000,
    "temperature": 0.7,
    "github_token": "",
    "last_repo_path": "",
    "auto_stage": False,
    "repositories": [],
}


class ConfigManager:
    _lock = threading.Lock()

    @staticmethod
    def _normalize_repo_path(repo_path: str) -> str:
        raw = (repo_path or "").strip()
        if not raw:
            return ""
        try:
            return str(Path(raw).resolve())
        except Exception:
            return os.path.normpath(raw)

    @staticmethod
    def _dedupe_repositories(repos: List[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for item in repos or []:
            if not isinstance(item, str):
                continue
            norm = ConfigManager._normalize_repo_path(item)
            if not norm:
                continue
            key = os.path.normcase(norm)
            if key not in seen:
                seen.add(key)
                result.append(norm)
        return result

    @staticmethod
    def _write_config_unlocked(config: dict):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

    @staticmethod
    def _load_config():
        """Load configuration from file, merging with defaults and optional env fallback."""
        with ConfigManager._lock:
            if not CONFIG_FILE.exists():
                ConfigManager._create_default_config()

            merged = DEFAULT_CONFIG.copy()
            merged["repositories"] = []
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        merged.update(loaded)
            except Exception:
                pass

            raw_repos = merged.get("repositories")
            if not isinstance(raw_repos, list):
                raw_repos = []

            last_repo = ConfigManager._normalize_repo_path(merged.get("last_repo_path", ""))
            if last_repo:
                merged["last_repo_path"] = last_repo
                raw_repos = list(raw_repos) + [last_repo]

            merged["repositories"] = ConfigManager._dedupe_repositories(raw_repos)

            env_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if (not merged.get("api_key") or merged.get("api_key") == "your-api-key-here") and env_key:
                merged["api_key"] = env_key

            return merged

    @staticmethod
    def _create_default_config():
        """Create default configuration file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)

        print(f"📝 Created config file at: {CONFIG_FILE}")
        print("⚠️  Please set your API key using: git-commit-ai config --set-key YOUR_KEY")

    @staticmethod
    def save_api_key(api_key: str):
        """Save API key to config."""
        config = ConfigManager._load_config()
        with ConfigManager._lock:
            config["api_key"] = api_key
            ConfigManager._write_config_unlocked(config)

        print("✅ API key saved successfully!")

    @staticmethod
    def save_model(model_name: str):
        """Save Model key to config."""
        config = ConfigManager._load_config()
        with ConfigManager._lock:
            config["model"] = model_name
            ConfigManager._write_config_unlocked(config)

        print("✅ Model key saved successfully!")

    @staticmethod
    def save_github_token(token: str):
        """Save GitHub token to config."""
        config = ConfigManager._load_config()
        with ConfigManager._lock:
            config["github_token"] = token
            ConfigManager._write_config_unlocked(config)

        print("✅ GitHub token saved successfully!")

    @staticmethod
    def save_settings(settings: dict):
        """Save a dictionary of settings to config."""
        config = ConfigManager._load_config()
        with ConfigManager._lock:
            config.update(settings)
            if "repositories" in config:
                config["repositories"] = ConfigManager._dedupe_repositories(config["repositories"])
            ConfigManager._write_config_unlocked(config)
        print("✅ Settings saved successfully!")

    @staticmethod
    def get_repositories() -> List[str]:
        """Return saved list of repository paths."""
        config = ConfigManager._load_config()
        return list(config.get("repositories", []))

    @staticmethod
    def add_repository(repo_path: str) -> List[str]:
        """Add or select a repository path in saved repositories and persist it."""
        norm_path = ConfigManager._normalize_repo_path(repo_path)
        if not norm_path:
            return ConfigManager.get_repositories()

        config = ConfigManager._load_config()
        with ConfigManager._lock:
            repos = ConfigManager._dedupe_repositories(config.get("repositories", []) + [norm_path])
            config["repositories"] = repos
            config["last_repo_path"] = norm_path
            ConfigManager._write_config_unlocked(config)
            return list(repos)

    @staticmethod
    def remove_repository(repo_path: str) -> List[str]:
        """Remove a repository path from saved repositories and update config."""
        norm_path = ConfigManager._normalize_repo_path(repo_path)
        target_key = os.path.normcase(norm_path)
        config = ConfigManager._load_config()
        with ConfigManager._lock:
            repos = [
                r for r in ConfigManager._dedupe_repositories(config.get("repositories", []))
                if os.path.normcase(r) != target_key
            ]
            config["repositories"] = repos
            if os.path.normcase(config.get("last_repo_path", "")) == target_key:
                config["last_repo_path"] = repos[0] if repos else ""
            ConfigManager._write_config_unlocked(config)
            return list(repos)

    @staticmethod
    def reset_to_default():
        """Reset config to default values."""
        with ConfigManager._lock:
            defaults = DEFAULT_CONFIG.copy()
            defaults["repositories"] = []
            ConfigManager._write_config_unlocked(defaults)
            return defaults

    @staticmethod
    def get_config():
        """Get configuration with validation."""
        config = ConfigManager._load_config()

        if config.get("api_key") == "your-api-key-here" or not config.get("api_key"):
            return 400, "API key not configured!"

        return 200, config


def create_default_config():
    return ConfigManager._create_default_config()


def get_config():
    return ConfigManager.get_config()


def save_api_key(api_key: str):
    return ConfigManager.save_api_key(api_key)


def save_model(model_name: str):
    return ConfigManager.save_model(model_name)


def save_github_token(token: str):
    return ConfigManager.save_github_token(token)

