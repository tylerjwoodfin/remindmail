import json
import os
import httplib2
from sys import exit
from datetime import datetime, timedelta
from typing import Optional
from oauth2client import tools
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from securedata import securedata

from remind.reminder_struc import Reminder

APP_KEYS_FILE = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'app_keys.json')
USER_OAUTH_DATA_FILE = os.path.expanduser('~/.google-reminders-cli-oauth')


def authenticate() -> httplib2.Http:
    """
    returns an Http instance that already contains the user credentials and is
    ready to make requests to alter user data.

    On the first time, this function will open the browser so that the user can
    grant it access to his data
    """
    app_keys = securedata.getItem("remindmail")
    try:
        client_id = app_keys['client_id']
        client_secret = app_keys['client_secret']
    except (KeyError, TypeError):
        securedata.log(
            "Missing Google client ID/client secret; see https://github.com/jonahar/google-reminders-cli and store these in securedata (see README)", level="error")
        exit(-1)

    storage = Storage(USER_OAUTH_DATA_FILE)
    credentials = storage.get()
    credentials_json = json.loads(credentials.to_json())
    securedata.setItem("remindmail", "refresh_token",
                       credentials_json['refresh_token'])

    if credentials is None:
        securedata.log(
            "RemindMail is has no credentials; please reauthorize", level="error")
        credentials = tools.run_flow(
            flow=OAuth2WebServerFlow(
                client_id=client_id,
                client_secret=client_secret,
                scope=['https://www.googleapis.com/auth/reminders'],
                user_agent='remindmail',
                access_type='offline',
            ),
            storage=storage,
            flags=tools.argparser.parse_args([]),
        )
    elif credentials.invalid:
        securedata.log(
            "RemindMail is unauthenticated from Google", level="warn")
        credentials.refresh(httplib2.Http())

    auth_http = credentials.authorize(httplib2.Http())
    return auth_http


def create_req_body(reminder: Reminder) -> str:
    """
    returns the body of a create-reminder request
    """
    body = {
        '2': {
            '1': 7
        },
        '3': {
            '2': reminder.id
        },
        '4': {
            '1': {
                '2': reminder.id
            },
            '3': reminder.title,
            '5': {
                '1': reminder.dt.year,
                '2': reminder.dt.month,
                '3': reminder.dt.day,
                '4': {
                    '1': reminder.dt.hour,
                    '2': reminder.dt.minute,
                    '3': reminder.dt.second,
                }
            },
            '8': 0
        }
    }
    return json.dumps(body)


def get_req_body(reminder_id: str) -> str:
    """
    returns the body of a get-reminder request
    """
    body = {'2': [{'2': reminder_id}]}
    return json.dumps(body)


def delete_req_body(reminder_id: str) -> str:
    """
    returns the body of a delete-reminder request
    """
    body = {'2': [{'2': reminder_id}]}
    return json.dumps(body)


def list_req_body(num_reminders: int, max_timestamp_msec: int = 0) -> str:
    """
    returns the body of a list-reminders request.

    The body corresponds to a request that retrieves a maximum of num_reminders
    reminders, whose creation timestamp is less than max_timestamp_msec.
    max_timestamp_msec is a unix timestamp in milliseconds. if its value is 0, treat
    it as current time.
    """
    body = {
        '5': 1,  # boolean field: 0 or 1. 0 doesn't work ¯\_(ツ)_/¯
        '6': num_reminders,  # number number of reminders to retrieve
    }

    if max_timestamp_msec:
        max_timestamp_msec += int(timedelta(hours=15).total_seconds() * 1000)
        body['16'] = max_timestamp_msec
        # Empirically, when requesting with a certain timestamp, reminders with the given
        # timestamp or even a bit smaller timestamp are not returned. Therefore we increase
        # the timestamp by 15 hours, which seems to solve this...  ~~voodoo~~
        # (I wish Google had a normal API for reminders)

    return json.dumps(body)


"""
Builds a JSON reminder object for client.py
"""


def build_reminder(reminder_dict: dict) -> Optional[Reminder]:
    r = reminder_dict
    header = ''

    # example r: {'1': {'1': '123412341234', '2': 'assistant_123412341234'}, '2': {'1': 16}, '3': 'go to bed', '5': {'1': 2021, '2': 4, '3': 18, '4': {'1': 21, '2': 0, '3': 0}, '9': 0}, '13': {'1': '6594819'}, '15': {}, '18': '1618725268661', '22': 1}
    if "5" in r:
        if "1" in r["5"] and "2" in r["5"] and "3" in r["5"]:
            year = r['5']['1']
            month = r['5']['2']
            day = r['5']['3']
            hour = r['5']['4']['1']
            dt = datetime(year, month, day).strftime("%m-%d").lower()
            header = f"[{dt}]d "

    id = r['1']['2']
    title = r['3']
    creation_timestamp_msec = int(r['18'])
    done = '8' in r and r['8'] == 1

    return {
        "id": id,
        "title": header + title,
        "creation_timestamp_msec": creation_timestamp_msec,
        "done": done,
        "target_date": datetime(year, month, day, hour)
    }
