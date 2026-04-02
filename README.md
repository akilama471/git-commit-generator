# git-commit-generator 🚀

## Description/Overview

This project leverages AI models to intelligently generate Git commit messages. It aims to streamline the commit process by providing context-aware suggestions for commit prefixes (e.g., `feat`, `fix`, `docs`, `chore`) and concise, descriptive commit messages. This tool helps maintain a clean and standardized commit history, making collaboration and code review more efficient.

## Features ✨

*   **AI-Powered Commit Generation:** Utilizes advanced AI models to understand code changes and generate relevant commit messages.
*   **Smart Prefix Suggestions:** Recommends conventional commit prefixes based on the nature of the changes.
*   **Concise Descriptions:** Crafts clear and to-the-point descriptions for each commit.
*   **Command-Line Interface (CLI):** Easy-to-use CLI for seamless integration into your Git workflow.
*   **Customizable Configuration:** Allows for adjustments to AI model parameters and output formatting.

## Installation Instructions 📚

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your_username/git-commit-generator.git
    cd git-commit-generator
    ```

2.  **Set up a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install the package:**
    ```bash
    pip install .
    ```

## Usage Examples 💡

Once installed, you can use the `git-commit-ai` command from your Git repository's root directory.

**Generate a commit message for staged changes:**

```bash
git commit-ai
```

This command will analyze your staged changes, generate a commit message, and prompt you to confirm or edit it before committing.

**Generate a commit message with a specific prompt:**

```bash
git commit-ai --prompt "Refactor user authentication module"
```

**Generate a commit message and directly commit without confirmation:**

```bash
git commit-ai --amend
```

**View help:**

```bash
git commit-ai --help
```

## Project Structure 📂

```
git-commit-generator/
├── requirements.txt
├── setup.py
├── __init__.py
├── core/
│   ├── ai_client.py
│   ├── cli.py
│   ├── config.py
│   ├── git_utils.py
│   ├── utils.py
│   └── __init__.py
└── git_commit_ai.egg-info/
    ├── dependency_links.txt
    ├── entry_points.txt
    ├── PKG-INFO
    ├── requires.txt
    ├── SOURCES.txt
    └── top_level.txt
```

*   `requirements.txt`: Lists all Python dependencies.
*   `setup.py`: Used for packaging and distribution.
*   `core/`: Contains the main logic of the application.
    *   `ai_client.py`: Handles interactions with the AI model.
    *   `cli.py`: Implements the command-line interface.
    *   `config.py`: Manages application configuration.
    *   `git_utils.py`: Provides utility functions for Git operations.
    *   `utils.py`: General utility functions.
*   `git_commit_ai.egg-info/`: Metadata for the installed package.

## Dependencies 🔗

The project relies on the following key dependencies (listed in `requirements.txt`):

*   Python 3.7+
*   [Specific AI library, e.g., OpenAI, Hugging Face Transformers]
*   [Other necessary Python packages, e.g., `click` for CLI]

Please refer to `requirements.txt` for a complete and up-to-date list.

## Configuration ⚙️

Configuration settings, such as API keys for AI models or preferred commit message formats, can be managed in `core/config.py`. You might also consider implementing environment variable support for sensitive information like API keys.

Example (conceptual):

```python
# core/config.py
import os

# API key for the AI model
AI_API_KEY = os.environ.get("AI_API_KEY", "your_default_api_key")

# Model name to use
AI_MODEL_NAME = "gpt-3.5-turbo" # or another suitable model

# Prefixes for commit messages
COMMIT_PREFIXES = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "chore"]
```

## Contributing Guidelines 🤝

We welcome contributions to `git-commit-generator`! Please follow these steps:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix.
3.  **Make your changes** and ensure they are well-tested.
4.  **Add tests** for any new functionality.
5.  **Update the documentation** if necessary.
6.  **Commit your changes** using conventional commit messages.
7.  **Push your branch** to your fork.
8.  **Submit a Pull Request** to the main repository.

Please ensure your code adheres to the project's coding style and passes all existing tests.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.