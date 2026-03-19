import sys
from colorama import Fore, Style
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import message_dialog
from prompt_toolkit.keys import Keys

def print_colored(message, color='white'):
    """Print colored message"""
    colors = {
        'red': Fore.RED,
        'green': Fore.GREEN,
        'yellow': Fore.YELLOW,
        'blue': Fore.BLUE,
        'cyan': Fore.CYAN,
        'magenta': Fore.MAGENTA,
        'white': Fore.WHITE
    }
    print(colors.get(color, Fore.WHITE) + message + Style.RESET_ALL)

def select_from_menu(options):
    """Simple menu selection"""
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    while True:
        try:
            choice = int(input("\nEnter your choice (1-{}): ".format(len(options))))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print_colored("Invalid choice. Try again.", 'red')
        except ValueError:
            print_colored("Please enter a number.", 'red')
        except KeyboardInterrupt:
            print("\n")
            sys.exit(0)

def edit_text(initial_text):
    """Simple text editor"""
    print("\n(Edit the text below, then press Enter twice to finish)")
    print("-" * 50)
    print(initial_text)
    print("-" * 50)
    
    lines = []
    print("Start editing (Enter a blank line to finish):")
    
    # Show current text as editable
    for line in initial_text.split('\n'):
        new_line = prompt(line, default=line)
        lines.append(new_line)
    
    # Allow adding more lines
    while True:
        line = prompt("")
        if not line:
            break
        lines.append(line)
    
    return '\n'.join(lines)