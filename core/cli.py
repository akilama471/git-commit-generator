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
from .config import create_default_config, get_config, save_api_key, save_model, save_github_token
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


@click.group(epilog="""\b
Shortcut Options (runs 'generate' automatically):
  -a, --add         Stage all changes first
  -c, --commit      Auto-commit after generation
  -m, --model TEXT  Ai model to use
  -y, --copy        Copy message to clipboard only
  -r, --readme      Generate README.md file for the repository
  -i, --issue       Generate an issue description
  \b
Shortcut Options (runs 'config' automatically):
  init              Initialize default configuration
  set-github-token  Set GitHub Personal Access Token
  set-key           Set AI API key
  set-model         Set AI Model key
  show              Show current configuration
""")
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
@click.option(
    "--issue", "-i", is_flag=True, help="Generate an issue description"
)
def generate(
    path: str, add: bool, commit: bool, model: Optional[str], copy: bool, readme: bool, issue: bool
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

        # Handle Issue generation if requested
        if issue:
            generate_issue_cmd(model)
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


def generate_issue_cmd(model: Optional[str] = None):
    """Generate a structured Issue"""
    print_colored("\n📋 Generating new Issue...", "cyan")

    try:
        context = click.prompt("Enter a short description of the issue or feature", type=str)
        if not context.strip():
            print_colored("❌ Description cannot be empty", "red")
            return

        # Load config
        config = get_config()

        # Initialize AI client
        use_model = model or config.get("model", "gemini-2.0-flash-lite")
        from .ai_client import GeminiClient as AIClient

        client = AIClient(
            api_key=config["api_key"],
            model=use_model,
            temperature=config.get("temperature", 0.7),
        )

        # Generate Issue content
        print_colored("🤖 Generating details...", "blue")
        issue_content = client.generate_issue(context)

        if not issue_content:
            print_colored("❌ Failed to generate issue", "red")
            return

        # Show preview
        print_colored("\n📝 Issue Preview:", "green")
        print(Fore.WHITE + "=" * 60)
        print(issue_content)
        print(Fore.WHITE + "=" * 60)

        # Prompt for next steps
        print("\n💾 What would you like to do?")
        print("  [y] Edit before proceeding")
        print("  [c] Copy to clipboard")
        print("  [s] Save to file (issue.md)")
        print("  [p] Publish directly to GitHub")
        print("  [n] Cancel")
        
        choice = click.prompt(
            "Select action", 
            type=click.Choice(['y', 'c', 's', 'p', 'n'], case_sensitive=False),
            default='c'
        ).lower()

        if choice == 'n':
            print_colored("❌ Issue generation cancelled", "yellow")
            return
            
        final_issue = issue_content
        
        if choice == 'y':
            print_colored("\nOpening your default text editor to review/edit the Issue...", 'cyan')
            edited_text = click.edit(text=issue_content)
            if edited_text is not None:
                final_issue = edited_text
            else:
                print_colored("No changes made in editor.", "blue")
                
            # Ask again what to do with the edited text
            print("\n💾 What now?")
            print("  [c] Copy to clipboard")
            print("  [s] Save to file (issue.md)")
            print("  [p] Publish directly to GitHub")
            second_choice = click.prompt(
                "Select action", 
                type=click.Choice(['c', 's', 'p'], case_sensitive=False),
                default='c'
            ).lower()
            choice = second_choice

        if choice == 'c':
            pyperclip.copy(final_issue)
            print_colored("✅ Issue copied to clipboard!", "green")
        elif choice == 's':
            with open("issue.md", "w", encoding="utf-8") as f:
                f.write(final_issue)
            print_colored(f"✅ Issue saved to issue.md", "green")
        elif choice == 'p':
            publish_issue_to_github(final_issue, config)

    except Exception as e:
        print_colored(f"❌ Error generating issue: {e}", "red")
        import traceback
        traceback.print_exc()
        
def publish_issue_to_github(issue_md: str, config: dict):
    """Publish generated issue markdown directly to GitHub via API"""
    token = config.get("github_token", "")
    if not token:
        print_colored("❌ GitHub token not configured!", "red")
        print("Please run: git-commit-ai config set-github-token YOUR_TOKEN")
        print("Get your token from: https://github.com/settings/tokens (requires 'repo' scope)")
        return

    # Extract owner and repo from remote
    from .git_utils import run_git_command
    stdout, _, code = run_git_command(["git", "config", "--get", "remote.origin.url"])
    if code != 0 or not stdout.strip():
        print_colored("❌ Could not get git remote 'origin' URL.", "red")
        return

    remote_url = stdout.strip()
    import re
    # Matches https://github.com/owner/repo(.git) or git@github.com:owner/repo(.git)
    match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$', remote_url)
    if not match:
        print_colored("❌ Could not parse GitHub owner and repo from remote origin URL.", "red")
        return

    owner = match.group(1)
    repo = match.group(2)

    # Simple title extraction: grab first non-empty line
    lines = issue_md.split('\n')
    title = "New Issue"
    body = issue_md
    
    for i, line in enumerate(lines):
        if line.strip():
            title = line.lstrip('# *').strip()
            # Remove the title line from the body
            body = '\n'.join(lines[i+1:]).strip()
            break

    print_colored(f"Publishing issue '{title}' to {owner}/{repo}...", "blue")
    import requests
    response = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        },
        json={"title": title, "body": body}
    )

    if response.status_code == 201:
        issue_url = response.json().get("html_url")
        print_colored(f"✅ Issue published successfully! URL: {issue_url}", "green")
        import webbrowser
        try:
            webbrowser.open(issue_url)
        except:
            pass
    else:
        print_colored(f"❌ Failed to publish issue. Status Code: {response.status_code}", "red")
        try:
            print(response.json())
        except:
            print(response.text)


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

        # Custom prompt for next steps
        print("\n💾 Proceed with README.md?")
        print("  [y] Edit before saving")
        print("  [s] Save directly (continue)")
        print("  [n] Cancel")
        
        choice = click.prompt(
            "Select action", 
            type=click.Choice(['y', 's', 'n'], case_sensitive=False),
            default='s'
        ).lower()

        if choice == 'n':
            print_colored("❌ README generation cancelled", "yellow")
            return
            
        final_readme = readme_content
        
        if choice == 'y':
            print_colored("\nOpening your default text editor to review/edit the README...", 'cyan')
            print_colored("Close the editor when you are finished. It will be saved automatically.", 'yellow')
            edited_text = click.edit(text=readme_content)
            
            # click.edit returns None if closed without modification
            if edited_text is not None:
                final_readme = edited_text
            else:
                print_colored("No changes made in editor. Proceeding with original generation.", "blue")

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


@config.command("set-github-token")
@click.argument("token")
def set_github_token(token):
    """Set GitHub Personal Access Token"""
    save_github_token(token)


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
