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

def edit_text(initial_text):
    """Multiline text editor using prompt_toolkit"""
    print_colored("\nEditing commit message:", 'cyan')
    print_colored("Press [Alt+Enter] or [Esc] followed by [Enter] to save and finish.", 'yellow')
    print("-" * 50)
    
    try:
        # Use prompt toolkit multiline input for better editing experience
        edited_text = prompt("> ", default=initial_text, multiline=True)
        return edited_text.strip()
    except KeyboardInterrupt:
        print("\n")
        sys.exit(0)
    except EOFError:
        print("\n")
        sys.exit(0)