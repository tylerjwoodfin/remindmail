"""
Test file for reminder confirmation functionality
"""
import os

tests = {
    "test1": "remind --title 'Test Dry Run' --when 'now' --dry-run",
    "test2": "remind --title 'Test Dry Run with Tags' --when 'tomorrow' --tags 'test,dry-run' --dry-run",
    "test3": "remind --title 'Test Dry Run with Notes' --when 'tomorrow' --notes 'This is a test note' --dry-run",
    "test4": "remind --title 'Test Dry Run Multiple' --when 'every 2 days' --dry-run"
}

for test, command in tests.items():
    print(f"\nRunning test {test}")
    print(f"Command: {command}")
    os.system(command)
    print(f"Test {test} complete") 