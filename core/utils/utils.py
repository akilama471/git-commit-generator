import sys
import click
from colorama import Fore, Style


def print_colored(message: str, color: str = "white"):
    """Print colored message."""
    colors = {
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "cyan": Fore.CYAN,
        "magenta": Fore.MAGENTA,
        "white": Fore.WHITE,
    }
    print(colors.get(color, Fore.WHITE) + message + Style.RESET_ALL)


def select_from_menu(options):
    """Simple menu selection."""
    for i, option in enumerate(options, 1):
        print_colored(f"\n[{i}] Option {i}:", "cyan")
        print(f"{option}")

    while True:
        try:
            choice_input = input(f"\nEnter your choice (1-{len(options)}): ").strip()
            if not choice_input:
                continue

            choice = int(choice_input)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            print_colored("Invalid choice. Please enter a valid number.", "red")
        except ValueError:
            print_colored("Please enter a number.", "red")
        except (KeyboardInterrupt, EOFError):
            print("\n")
            sys.exit(0)


def edit_text(initial_text: str) -> str:
    """Multiline text editor using click.edit (opens system editor)."""
    print_colored("\nOpening your default text editor to modify the commit message...", "cyan")
    print_colored("Save and close the editor when you are finished.", "yellow")
    print("-" * 50)

    edited_text = click.edit(text=initial_text)

    if edited_text is None:
        print_colored("Editing cancelled. Keeping original text.", "yellow")
        return initial_text.strip()

    return edited_text.strip()


class CommitService:
    def __init__(self, commit_generator):
        self.commit_generator = commit_generator

    @staticmethod
    def print_colored(message: str, color: str = "white"):
        print_colored(message, color)

    @staticmethod
    def select_from_menu(options):
        return select_from_menu(options)

    @staticmethod
    def edit_text(initial_text: str) -> str:
        return edit_text(initial_text)