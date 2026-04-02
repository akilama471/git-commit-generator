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
        print_colored(f"\n[{i}] Option {i}:", 'cyan')
        print(f"{option}")
    
    while True:
        try:
            choice_input = input("\nEnter your choice (1-{}): ".format(len(options))).strip()
            if not choice_input:
                continue
                
            choice = int(choice_input)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print_colored("Invalid choice. Please enter a valid number.", 'red')
        except ValueError:
            print_colored("Please enter a number.", 'red')
        except KeyboardInterrupt:
            print("\n")
            sys.exit(0)
        except EOFError:
            print("\n")
            sys.exit(0)

import click

def edit_text(initial_text):
    """Multiline text editor using click.edit (opens system editor)"""
    print_colored("\nOpening your default text editor to modify the commit message...", 'cyan')
    print_colored("Save and close the editor when you are finished.", 'yellow')
    print("-" * 50)
    
    # Opens Notepad/Vim/etc and returns the modified text when closed.
    edited_text = click.edit(text=initial_text)
    
    # If the user closed without changing anything or aborted it could return None
    if edited_text is None:
        print_colored("Editing cancelled. Keeping original text.", 'yellow')
        return initial_text.strip()
        
    return edited_text.strip()