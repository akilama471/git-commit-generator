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
}

class ConfigManager:
    
    def _load_config():
        """Load configuration from file"""
        if not CONFIG_FILE.exists():
            ConfigManager._create_default_config()

        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)

        return config


    def _create_default_config():
        """Create default configuration file"""
        CONFIG_DIR.mkdir(exist_ok=True)

        with open(CONFIG_FILE, "w") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)

        print(f"📝 Created config file at: {CONFIG_FILE}")
        print("⚠️  Please set your API key using: git-commit-ai config --set-key YOUR_KEY")


    def save_api_key(api_key):
        """Save API key to config"""
        config = ConfigManager._load_config()
        config["api_key"] = api_key

        with open(CONFIG_FILE, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print("✅ API key saved successfully!")


    def save_model(model_name):
        """Save Model key to config"""
        config = ConfigManager._load_config()
        config["model"] = model_name

        with open(CONFIG_FILE, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print("✅ Model key saved successfully!")


    def save_github_token(token):
        """Save GitHub token to config"""
        config = ConfigManager._load_config()
        config["github_token"] = token

        with open(CONFIG_FILE, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print("✅ GitHub token saved successfully!")

    @staticmethod
    def save_settings(settings: dict):
        """Save a dictionary of settings to config"""
        config = ConfigManager._load_config()
        config.update(settings)
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("✅ Settings saved successfully!")

    @staticmethod
    def reset_to_default():
        """Reset config to default values while optionally keeping api_key if needed"""
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(DEFAULT_CONFIG.copy(), f, default_flow_style=False)
        return DEFAULT_CONFIG.copy()

    @staticmethod
    def get_config():
        """Get configuration with validation"""
        config = ConfigManager._load_config()

        if config.get("api_key") == "your-api-key-here" or not config.get("api_key"):
            return 400, "API key not configured!"

        return 200, config

