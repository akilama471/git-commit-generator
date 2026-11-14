import os
from pathlib import Path
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
}


class ConfigManager:
    @staticmethod
    def _load_config():
        """Load configuration from file, merging with defaults and optional env fallback."""
        if not CONFIG_FILE.exists():
            ConfigManager._create_default_config()

        merged = DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    merged.update(loaded)
        except Exception:
            pass

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
        config["api_key"] = api_key

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

        print("✅ API key saved successfully!")

    @staticmethod
    def save_model(model_name: str):
        """Save Model key to config."""
        config = ConfigManager._load_config()
        config["model"] = model_name

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

        print("✅ Model key saved successfully!")

    @staticmethod
    def save_github_token(token: str):
        """Save GitHub token to config."""
        config = ConfigManager._load_config()
        config["github_token"] = token

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

        print("✅ GitHub token saved successfully!")

    @staticmethod
    def save_settings(settings: dict):
        """Save a dictionary of settings to config."""
        config = ConfigManager._load_config()
        config.update(settings)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("✅ Settings saved successfully!")

    @staticmethod
    def reset_to_default():
        """Reset config to default values."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_CONFIG.copy(), f, default_flow_style=False)
        return DEFAULT_CONFIG.copy()

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

