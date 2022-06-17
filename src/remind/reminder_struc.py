import functools
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


def gen_id() -> str:
    """generate a fresh reminder id"""
    # id is set according to the current unix time
    return f'cli-reminder-{time.time()}'


@dataclass
@functools.total_ordering
class Reminder:
    id: str
    title: str
    dt: datetime
    creation_timestamp_msec: Optional[int] = None
    done: bool = False
    
    def __lt__(self, other):
        return self.id < other.id

    def __done__(self):
        return "DONE" if self.done else "TODO"

    def __repr__(self):
        format = '%Y-%m-%d %H:%M'
        return f'{self.__done__()} {self.dt.strftime(format)}: {self.title} ; id="{self.id}"'
