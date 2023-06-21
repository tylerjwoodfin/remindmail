"""
Used to manage Trello connections
"""
import requests
from cabinet import Cabinet


class TrelloManager:
    """
    A class for managing Trello boards and lists.
    """

    def __init__(self, board_name: str = None):
        self.cab = Cabinet()
        self.api_key = self.cab.get("keys", "trello")
        self.api_secret = self.cab.get("trello", "secret")
        self.api_token = self.cab.get("trello", "token")
        self.board_name = board_name or self.cab.get("trello", "board")

        if self.board_name is None:
            boards = self.list_all_boards()
            board_index = -1
            while board_index < 0:
                board_input = input("\nWhich board would you like to use?\n")
                try:
                    board_index = int(board_input) - 1
                except ValueError:
                    print("Enter a valid number.")
            self.board_name = boards[board_index]['name']

    def obtain_token(self):
        """
        Obtains the token for Trello.
        """
        if self.api_token is None:
            auth_url = (
                f"https://trello.com/1/authorize?"
                f"key={self.api_key}&name=RemindMail&scope=read,write"
                "&expiration=never&response_type=token"
            )
            print(
                f"Please go to the following URL "
                f"and grant access to your Trello account:\n{auth_url}"
            )

            self.api_token = input("Enter the generated token: ")
            self.cab.put("trello", "token", self.api_token)

    def get_board_id(self, board_name):
        """
        Gets the board ID for the specified board name.

        Args:
            board_name (str): The name of the Trello board.

        Returns:
            str: The ID of the Trello board if found, None otherwise.
        """

        url = (f"https://api.trello.com/1/members/me/boards?"
               f"key={self.api_key}&token={self.api_token}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        board_id = None
        for board in response.json():
            if board['name'] == board_name:
                board_id = board['id']
                break

        return board_id

    def get_lists_on_board(self, board_id):
        """
        Gets the lists on a Trello board.

        Args:
            board_id (str): The ID of the Trello board.

        Returns:
            list: A list of dictionaries representing the lists on the board.
        """
        url = (f"https://api.trello.com/1/boards/"
               f"{board_id}/lists?key={self.api_key}&token={self.api_token}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        return response.json()

    def add_item_to_list(self, list_id, item_name):
        """
        Adds an item to a list.
        """
        url = "https://api.trello.com/1/cards"
        params = {
            'key': self.api_key,
            'token': self.api_token,
            'name': item_name,
            'desc': 'Added from RemindMail',
            'pos': 'top',
            'idList': list_id
        }
        response = requests.post(url, params=params, timeout=10)
        response.raise_for_status()

    def show_lists(self, is_quiet=False):
        """
        Shows a numbered list of lists in the Trello board.

        Args:
            is_quiet (bool): Whether to print the lists or not.

        Returns:
            list: A list of dictionaries representing the lists on the Trello board.
        """
        board_id = self.get_board_id(self.board_name)
        lists = None

        if board_id:
            lists = self.get_lists_on_board(board_id)
            if not is_quiet:
                for index, list_info in enumerate(lists, start=1):
                    list_name = list_info['name']
                    print(f"{index}. {list_name}")
        else:
            print(f"Board '{self.board_name}' not found.")

        return lists

    def add_item(self, list_index=None, item_name=None):
        """
        Adds an item to a Trello list.

        Args:
            list_id (str): The ID of the Trello list.
            item_name (str): The name of the item to add.
        """
        board_id = self.get_board_id(self.board_name)
        if board_id:
            lists = self.get_lists_on_board(board_id)
            if 0 <= list_index < len(lists):
                list_id = lists[list_index]['id']
                self.add_item_to_list(list_id, item_name)
                print(
                    f"\n'{item_name}' added to {lists[list_index]['name']}.")
            else:
                print("Invalid list index.")
        else:
            print(f"Board '{self.board_name}' not found.")

    def show_items(self, list_index):
        """
        Shows the items in the selected list.
        """
        board_id = self.get_board_id(self.board_name)
        if board_id:
            lists = self.get_lists_on_board(board_id)
            if 0 <= list_index < len(lists):
                list_id = lists[list_index]['id']
                url = (f"https://api.trello.com/1/lists/{list_id}/"
                       f"cards?key={self.api_key}&token={self.api_token}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                items = response.json()
                for item in items:
                    item_name = item['name']
                    print(item_name)
            else:
                print("Invalid list index.")
        else:
            print(f"Board '{self.board_name}' not found.")

    def list_all_boards(self):
        """
        Lists all available Trello boards for the authorized user.

        Returns:
            list: A list of dictionaries representing the available boards.
        """
        url = (f"https://api.trello.com/1/members/me/boards"
               f"?key={self.api_key}&token={self.api_token}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        boards = response.json()
        for index, board in enumerate(boards, start=1):
            board_name = board['name']
            print(f"{index}. {board_name}")

        return boards

    def main(self):
        """
        Main function.
        """
        print("Direct invokation of Trello is not yet implemented.")


if __name__ == '__main__':
    trello_manager = TrelloManager()
    trello_manager.main()
