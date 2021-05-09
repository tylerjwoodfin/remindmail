# RaspberryPi-Tasks Overview
Manages my To Do list with support for Google Assistant integration and automatically generated tasks.

## Features
- Easily manage your To Do list from anywhere in the terminal
- Schedule one-time or recurring tasks
- Automatically sync as a plaintext file with Dropbox, Google Drive, Nextcloud, or any other Cloud Storage provider using [rclone](https://rclone.org/install/)

# Setup
- Install Python3
- Download [SecureData.py](https://github.com/tylerjwoodfin/SecureData) and place it somewhere useful 
- Modify the line starting with `securePath=` in SecureData.py to point to where you want to store metadata from `tasks config`
  - Use full paths instead of relative paths, e.g. use `/home/pi/SecureData-Data/` instead of `~/SecureData-Data`
- Now, we need somewhere to locally store your Tasks.txt file. We'll call it "notespath". In Terminal, run:
  - `tasks config notespath "/full/path/to/notes"`

## Sync with Cloud Storage providers using Rclone (optional)
- Complete the steps above in "Setup"
- Install [rclone](https://rclone.org/install/).
- Run `rclone config` to set up a cloud storage provider of your choice
- Run `cd /path/to/{securePath} && rclone listremotes > PiTasksCloudProvider`
- Run `cd /path/to/{securePath} && echo "/path/to/your/notesDir/in/cloud" > PiTasksCloudProviderPath`
  - For example, if you want to store Tasks.txt in the "Notes" folder in Dropbox, run `echo "Notes" > PiTasksCloudProviderPath`
  - For example, if you want to store Tasks.txt in the "Documents/Notes" folder in Dropbox, run `echo "Documents/Notes" > PiTasksCloudProviderPath`
- Note: if `PiTasksCloudProviderPath` or `PiTasksCloudProvider` are missing or incorrect, tasks will not sync.

# TasksGenerate.md
Files in `TasksGenerate.md` (to be placed in the same folder as Tasks.txt), will be added to Tasks.txt depending on the syntax below. This is very useful for automatically scheduling tasks.

# TasksGenerate.md example:
```
[mon]   This task is added if today is Monday.
[thu]   This task is added if today is Thursday.
[D01]   This task is added if today is the 1st of the month.
[D31]   This task is added if today is the 31st of the month.
[12-31] This task is added if today is December 31.
[1-5]   This task is added if today is January 5. (not tested on non-US systems)
[M%2]   This task is added if today is the first day of an even-numbered month (try other modulo examples: https://www.wolframalpha.com/input/?i=6%252)
[W%3]   This task is added if today is a Sunday of every third week, based on Epoch Time. See instructions below...
[D%4]   This task is added every 4 days.
[W%3+1] This task is added if today is a Sunday of every third week, _with an offset of 1_, meaning if [W%3] would normally be added last week, it will be added this week instead.
[M%2]d  This task is added at the next even-numbered month, then deleted from TasksGenerate.md. 
```

## Bad Examples:
```
[Monday] You must use sun, mon, tue, wed, thu, fri, or sat. Capitalization doesn't matter.
[D50] Months only have up to 31 days.
[Y%5] Year is unsupported.
(thu) You must use brackets.
{thu} You must use brackets.
  [W%3] You must start tasks on the first column.
[W%3-1] This is invalid. To add an offset, you MUST use +.
[W%3+4] This is also invalid and mathematically impossible. An offset of 4 makes no sense because [W%3+1] offsets 1 week, [W%3+2] offsets 2 weeks, and [W%3+3] is the same thing as [W%3]. [W%3+4] is the same as [W%3+1]- you should use this instead.
```

# How to use, assuming Linux:
- type "crontab -e" in the terminal

- Add the line below (without the >, without the #, replacing the path with your real path):
> 0 * * * * python3 path/to/tasks.py generate


# Using % to set "every n weeks", "every n days", "every n months":
## Overview
- The Epoch time is the number of seconds since January 1, 1970, UTC.
- For example, if the current time is 1619394350, then today is Sunday, April 25, 2021 at 11:45:50PM UTC.
- The "week number" is calculated by {epochTime}/60/60/24/7.
    - 1619394350 /60/60/24/7 ~= 2677
    - 2677 % 3 == 1, meaning scheduling a task for [W%3] would be added last week, but not this week (or next week or the week after).

## How to calculate

# using "d" to set one-time tasks:
- [D%5]d will add the task if 