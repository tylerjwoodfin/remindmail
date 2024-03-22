"""
The main entrypoint
"""

from . import remix_utils

def main():
    """
    The main function
    """

    utils = remix_utils.RemindmailUtils()

    # generate
    utils.generate()

if __name__ == "__main__":
    main()
