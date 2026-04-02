import io
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional  # Add this import

import click
import pyperclip
from colorama import Fore, Style, init
from prompt_toolkit import prompt

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .ai_client import GeminiClient  # Or whichever client you're using
from .config import create_default_config, get_config, save_api_key, save_model
from .git_utils import (
    commit_with_message,
    get_repo_info,
    get_repository_root,
    get_staged_diff,
    run_git_command,
    stage_all_changes,
)
from .utils import edit_text, print_colored, select_from_menu

# Initialize colorama for Windows
init(autoreset=True)


@click.group()
def cli():
    """AI-powered Git commit message generator using DeepSeek"""
    pass


@cli.command()
@click.argument("path", required=False, default=".")
@click.option("--add", "-a", is_flag=True, help="Stage all changes first")
@click.option("--commit", "-c", is_flag=True, help="Auto-commit after generation")
@click.option("--model", "-m", help="Ai model to use")
@click.option("--copy", "-y", is_flag=True, help="Copy message to clipboard only")
@click.option(
    "--readme", "-r", is_flag=True, help="Generate README.md file for the repository"
)
def generate(
    path: str, add: bool, commit: bool, model: Optional[str], copy: bool, readme: bool
):
    """Generate commit message for staged changes

    PATH can be:
       - Current directory: .
       - Relative path: ./my-project
       - Absolute path: M:/Projects/my-project
    """

    # Change to specified directory if provided
    original_dir = os.getcwd()
    try:
        # Resolve the path
        target_path = Path(path).resolve()

        if not target_path.exists():
            print_colored(f"❌ Path does not exist: {target_path}", "red")
            sys.exit(1)

        if not target_path.is_dir():
            print_colored(f"❌ Path is not a directory: {target_path}", "red")
            sys.exit(1)

        # Change to the target directory
        os.chdir(target_path)
        print_colored(f"📁 Changed to directory: {target_path}", "cyan")

        # Check if we're in a git repository
        repo_root = get_repository_root()
        if not repo_root:
            print_colored("❌ Not in a git repository!", "red")
            sys.exit(1)

        print_colored(f"📁 Repository: {repo_root}", "cyan")

        # Handle README generation if requested
        if readme:
            generate_readme(repo_root, model)
            return

        # Stage all changes if requested
        if add:
            print_colored("📦 Staging all changes...", "blue")
            if not stage_all_changes():
                print_colored("❌ Failed to stage changes", "red")
                sys.exit(1)
            print_colored("✅ Changes staged", "green")

        # Get staged diff
        git_diff = get_staged_diff()
        if not git_diff or not git_diff.diff:
            print_colored("❌ No staged changes found!", "yellow")
            print("Use --add to stage all changes or run 'git add' first")
            sys.exit(1)

        # Show files to be committed
        print_colored(f"\n📄 Files to commit ({len(git_diff.files)}):", "cyan")
        for file in git_diff.files[:10]:  # Show first 10 files
            print(f"   📄 {file}")
        if len(git_diff.files) > 10:
            print(f"   ... and {len(git_diff.files) - 10} more")

        # Load config
        config = get_config()

        # Initialize AI client
        use_model = model or config.get("model", "gemini-2.0-flash-lite")
        client = GeminiClient(
            api_key=config["api_key"],
            model=use_model,
            max_diff_len=config["max_diff_length"],
            temperature=config.get("temperature", 0.7),
        )

        # Generate messages
        print_colored("\n🤖 Generating commit messages...", "blue")
        options = client.generate_commit_messages(git_diff.diff)

        if not options:
            print_colored("❌ Failed to generate commit messages", "red")
            sys.exit(1)

        # Add custom option
        options.append("✏️  Write custom message")

        # Let user select
        print_colored("\n📝 Select a commit message:", "green")
        selected = select_from_menu(options)

        if selected == "✏️  Write custom message":
            selected = click.prompt("Enter your commit message")
        elif copy:
            # Copy to clipboard and exit
            pyperclip.copy(selected)
            print_colored("✅ Message copied to clipboard!", "green")
            return

        # Allow editing
        print_colored("\n✏️  Edit message (or press Enter to keep):", "yellow")
        edited = edit_text(selected)

        # Show final message
        print_colored("\n📝 Final commit message:", "green")
        print(Fore.WHITE + "─" * 50)
        print(edited)
        print(Fore.WHITE + "─" * 50)

        if copy:
            pyperclip.copy(edited)
            print_colored("✅ Message copied to clipboard!", "green")
            return

        # Confirm commit
        if not commit:
            if not click.confirm("\n💾 Proceed with commit?"):
                print_colored("❌ Commit cancelled", "yellow")
                return

        # Perform commit
        print_colored("💾 Committing...", "blue")
        if commit_with_message(edited):
            print_colored("✅ Commit successful!", "green")
        else:
            print_colored("❌ Commit failed", "red")

    finally:
        # Change back to original directory
        os.chdir(original_dir)
        print_colored(f"\n📁 Returned to: {original_dir}", "cyan")


def generate_readme(repo_path: str, model: Optional[str] = None):
    """Generate README.md for the repository"""

    print_colored("\n📖 Generating README.md for repository...", "cyan")

    try:
        # Get repository information
        repo_info = get_repo_info(repo_path)

        # Load config
        config = get_config()

        # Initialize AI client
        use_model = model or config.get("model", "gemini-2.0-flash-lite")

        from .ai_client import GeminiClient as AIClient

        client = AIClient(
            api_key=config["api_key"],
            model=use_model,
            max_diff_len=config.get("max_diff_length", 5000),
            temperature=config.get("temperature", 0.7),
        )

        # Generate README content
        print_colored("🤖 Generating README content...", "blue")
        readme_content = generate_readme_content(client, repo_info)

        if not readme_content:
            print_colored("❌ Failed to generate README content", "red")
            return

        # Show preview
        print_colored("\n📝 README Preview:", "green")
        print(Fore.WHITE + "=" * 60)
        print(readme_content[:1000] + ("..." if len(readme_content) > 1000 else ""))
        print(Fore.WHITE + "=" * 60)

        # Confirm before writing
        if not click.confirm("\n💾 Proceed to edit and save README.md?"):
            print_colored("❌ README generation cancelled", "yellow")
            return
            
        print_colored("\nOpening your default text editor to review/edit the README...", 'cyan')
        print_colored("Save and close the editor when you are finished.", 'yellow')
        final_readme = click.edit(text=readme_content)
        
        if final_readme is None:
            print_colored("❌ Editing cancelled. README will not be saved.", "yellow")
            return

        # Write to file
        readme_path = Path(repo_path) / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(final_readme)

        print_colored(f"✅ README.md successfully created at: {readme_path}", "green")

        # Ask if user wants to stage and commit the README
        if click.confirm("\n📦 Stage and commit the README.md?"):
            stage_all_changes()
            commit_message = f"docs: add comprehensive README documentation"
            if commit_with_message(commit_message):
                print_colored("✅ README committed successfully!", "green")
            else:
                print_colored("❌ Failed to commit README", "red")

    except Exception as e:
        print_colored(f"❌ Error generating README: {e}", "red")
        import traceback

        traceback.print_exc()


def generate_readme_content(client, repo_info: dict) -> str:
    """Generate README content using AI"""

    prompt = f"""Generate a comprehensive README.md for a git repository with the following information:

Repository Name: {repo_info["name"]}
Description: {repo_info["description"] or "No description provided"}
Primary Language: {repo_info["primary_language"]}
Languages: {", ".join(repo_info["languages"]) if repo_info["languages"] else "Not detected"}
Files/Directories: {", ".join(repo_info["top_files"][:15])}

Please create a professional README.md with these sections:
1. Project Title (using repo name)
2. Description/Overview
3. Features
4. Installation Instructions
5. Usage Examples
6. Project Structure
7. Dependencies
8. Configuration
9. Contributing Guidelines
10. License

Use markdown formatting with appropriate headers, code blocks, and lists.
Make it professional, comprehensive, and tailored to the project's actual content.
Include emojis for visual appeal where appropriate.
Ensure all code examples are in the correct language based on the project's primary language.
"""

    try:
        # Use the AI client to generate README using the new dedicated method
        readme_output = client.generate_readme(prompt)

        if readme_output:
            return readme_output
        else:
            # Fallback to basic template if AI fails
            return generate_basic_readme(repo_info)

    except Exception as e:
        print_colored(f"⚠️  AI generation failed, using template: {e}", "yellow")
        return generate_basic_readme(repo_info)


def generate_basic_readme(repo_info: dict) -> str:
    """Generate a basic README template"""

    name = repo_info["name"]
    description = (
        repo_info["description"] or "A Git repository with AI-powered features"
    )
    lang = repo_info["primary_language"] or "Unknown"
    languages = repo_info.get("languages", [])

    # Create language badge
    lang_badge = (
        f"![Language](https://img.shields.io/badge/language-{lang.replace(' ', '%20')}-blue.svg)"
        if lang != "Unknown"
        else ""
    )

    # Create top files section
    top_files_section = ""
    if repo_info.get("top_files"):
        top_files_section = "\n### 📁 Key Files\n\n"
        for file in repo_info["top_files"][:10]:
            top_files_section += f"- `{file}`\n"

    # Create languages section
    langs_section = ""
    if languages:
        langs_section = "\n### 🛠️ Technologies\n\n"
        for l in languages[:10]:
            langs_section += f"- {l}\n"

    # Create license section
    license_section = ""
    if repo_info.get("has_license"):
        license_section = "This project is licensed under the MIT License - see the LICENSE file for details."
    else:
        license_section = "This project is currently unlicensed. Please contact the maintainers for licensing information."

    return f"""# {name} 📦

{lang_badge}

## 📖 Description

{description}

## ✨ Features

- AI-powered git commit message generation
- Automated documentation
- Git workflow optimization
- Intelligent code analysis

## 📋 Prerequisites

- Git
- Python 3.8+
- {lang} (if applicable)

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/{name}.git

# Navigate to project directory
cd {name}

# Install dependencies (if any)
# pip install -r requirements.txt  # For Python projects
# npm install                       # For Node.js projects

## 💻 Usage

# Basic usage
git-commit-ai --add --commit

# Generate README
git-commit-ai --readme

# Specify different project path
git-commit-ai /path/to/project --add

# Set custom model
git-commit-ai --model "gemini-2.0-flash-lite"
{top_files_section}
{langs_section}

📁 Project Structure
text
{name}/
├── src/           # Source code
├── tests/         # Test files
├── docs/          # Documentation
└── README.md      # This file

🤝 Contributing

Fork the repository

Create your feature branch (git checkout -b feature/AmazingFeature)

Commit your changes (git-commit-ai --add --commit)

Push to the branch (git push origin feature/AmazingFeature)

Open a Pull Request

📄 License
{license_section}

🙏 Acknowledgments
Built with Python

Powered by AI

Inspired by modern development workflows

Generated with ❤️ using Git Commit AI on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""


@cli.group()
def config():
    """Configuration commands"""
    pass


@config.command("set-key")
@click.argument("api_key")
def set_key(api_key):
    """Set AI API key"""
    save_api_key(api_key)


@config.command("set-model")
@click.argument("model_name")
def set_model(model_name):
    """Set AI Model key"""
    save_model(model_name)


@config.command("show")
def show_config():
    """Show current configuration"""
    config = get_config()
    print_colored("Current Configuration:", "cyan")
    for key, value in config.items():
        if key == "api_key":
            value = value[:5] + "..." + value[-5:] if len(value) > 10 else "***"
        print(f"  {key}: {value}")


@config.command("init")
def init_config():
    """Initialize default configuration"""
    create_default_config()
    print_colored("✅ Configuration initialized!", "green")


@cli.command()
def status():
    """Show git status with AI context"""
    stdout, stderr, code = run_git_command(["git", "status"])
    if code == 0:
        print(stdout)
    else:
        print_colored(f"❌ Error: {stderr}", "red")


def main():
    """Entry point with better default command handling"""
    # If no arguments, assume generate
    if len(sys.argv) == 1:
        sys.argv.append("generate")
    # If the first argument is not one of the main commands or global help, map it to generate.
    # This allows `git-commit-ai -c` to evaluate as `git-commit-ai generate -c`
    elif sys.argv[1] not in ["generate", "config", "status", "--help", "-h"]:
        sys.argv.insert(1, "generate")
        
    cli()


if __name__ == "__main__":
    main()
