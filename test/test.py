"""
A work-in-progress set of tests for remindmail
"""
# pylint: disable=line-too-long

import os

tests: dict = {
    "test1": "remind --title test --when tomorrow",
    "test2": "remind --title test --when tomorrow --save",
    "test3": "remind --title test --when tomorrow --notes test",
    "test4": "remind --title test --when tomorrow --notes test --save",
    "test5": "remind --title test --when tomorrow --notes test --save --edit",
    "test6": "remind --title test --when tomorrow --notes test --save --edit --show-tomorrow",
    "test7": "remind --edit",
    "test8": "remind --show-tomorrow",
    "test9": "remind --later",
    "test10": "remind --show-week",
}

for test, command in tests.items():
    print(f"Running test {test}")
    os.system(command)
    print(f"Test {test} complete")
