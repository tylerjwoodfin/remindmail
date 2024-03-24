"""
The main entrypoint
"""

from . import reminder_manager

def main():
    """
    The main function
    """

    utils = reminder_manager.RemindmailUtils()

    # generate
    print("DEBUG")
    # utils.generate(True)
    utils.show_later()

if __name__ == "__main__":
    main()
