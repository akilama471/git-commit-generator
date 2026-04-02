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


def load_config():
    """Load configuration from file"""
    if not CONFIG_FILE.exists():
        create_default_config()

    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)

    return config


def create_default_config():
    """Create default configuration file"""
    CONFIG_DIR.mkdir(exist_ok=True)

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)

    print(f"📝 Created config file at: {CONFIG_FILE}")
    print("⚠️  Please set your API key using: git-commit-ai config --set-key YOUR_KEY")


def save_api_key(api_key):
    """Save API key to config"""
    config = load_config()
    config["api_key"] = api_key

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print("✅ API key saved successfully!")


def save_model(model_name):
    """Save Model key to config"""
    config = load_config()
    config["model"] = model_name

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print("✅ Model key saved successfully!")


def save_github_token(token):
    """Save GitHub token to config"""
    config = load_config()
    config["github_token"] = token

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print("✅ GitHub token saved successfully!")


def get_config():
    """Get configuration with validation"""
    config = load_config()

    if config.get("api_key") == "your-api-key-here" or not config.get("api_key"):
        print("❌ API key not configured!")
        print("Please run: git-commit-ai config --set-key YOUR_API_KEY")
        print("Get your API key from: https://platform.deepseek.com/")
        exit(1)

    return config
