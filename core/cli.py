import io
import sys

import click
import pyperclip
from colorama import Fore, Style, init
from prompt_toolkit import prompt

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .ai_client import GeminiClient  # Or whichever client you're using
from .config import create_default_config, get_config, save_api_key
from .git_utils import (
    commit_with_message,
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
@click.option("--add", "-a", is_flag=True, help="Stage all changes first")
@click.option("--commit", "-c", is_flag=True, help="Auto-commit after generation")
@click.option("--model", "-m", help="DeepSeek model to use")
@click.option("--copy", "-y", is_flag=True, help="Copy message to clipboard only")
def generate(add, commit, model, copy):
    """Generate commit message for staged changes"""

    # Check if we're in a git repository
    repo_root = get_repository_root()
    if not repo_root:
        print_colored("❌ Not in a git repository!", "red")
        sys.exit(1)

    print_colored(f"📁 Repository: {repo_root}", "cyan")

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
    if len(sys.argv) == 1:
        # No arguments, run generate
        sys.argv.append("generate")
    elif sys.argv[1] not in [
        "generate",
        "config",
        "status",
        "--help",
        "-h",
    ] and not sys.argv[1].startswith("-"):
        # If first argument isn't a command but looks like an option, insert 'generate'
        sys.argv.insert(1, "generate")
    cli()


if __name__ == "__main__":
    main()
