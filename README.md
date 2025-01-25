# RemindMail: Reminder Management Tool
A powerful CLI designed to help you schedule and organize reminders efficiently and effectively. 
Easily manage your To Do list, schedule one-time or recurring reminders, add notes, and view and manage upcoming reminders, all from the comfort of your terminal.

## Table of Contents
- [Features](#features)
- [Dependencies](#dependencies)
- [Installation and Setup](#installation-and-setup)
  - [Full Install (recommended)](#full-install-recommended)
  - [Minimal Install (experimental)](#minimal-install-experimental)
  - [Cabinet Configuration](#cabinet-configuration)
  - [Scheduling Reminder Emails](#scheduling-reminder-emails)
- [Usage](#usage)
  - [Scheduling Reminders With TUI](#scheduling-reminders-with-tui)
    - [VI Mode and Keybindings](#vi-mode-and-keybindings)
  - [Scheduling Reminders With remind.md](#scheduling-reminders-with-remindmd)
    - [Tags](#tags)
    - [Frequency](#frequency)
    - [Offset](#offset)
    - [Good Examples](#good-examples)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)
- [Author Info](#author-info)

# Features
RemindMail offers a variety of features to enhance your productivity:

- Easily manage your To Do list from anywhere in the terminal
- Send one-time or recurring reminders to your inbox
- Add notes or "for later" reminders
- View and manage upcoming reminders

# Dependencies
- `zsh` or `bash`
- `python3`
- [cabinet](https://pypi.org/project/cabinet/)
  - used to store the `remind.md` path and other important variables
- a configured SMTP server (many email providers offer this, but Gmail will not work)

# Installation and Setup

## Full Install (recommended)
```bash
  pip install remindmail

  # adjust path accordingly
  pip install -r requirements.md

  cabinet --configure # see below for instructions
```

## Minimal Install (experimental)
```bash
curl -s https://api.github.com/repos/tylerjwoodfin/remindmail/releases/latest \
| grep "browser_download_url" \
| cut -d '"' -f 4 \
| xargs curl -L -o remindmail.pex

sudo mv remindmail.pex /usr/local/bin/remind

remind -m cabinet --config
```

## Cabinet Configuration
- [cabinet](https://github.com/tylerjwoodfin/cabinet) is installed as a dependency.

- initialize using `cabinet --configure`; see cabinet's README for details.

- add the properties below using `cabinet -e`:
```json
{
  "remindmail": {
      "path": {
          "file": "/path/to/remind.md"
      }
  },
  "email": {
      "from": "YourUniqueAndNonGmailEmailAddress",
      "from_pw": "YourPassword",
      "from_name": "Your Name",
      "to": "RemindersSentToThisEmailAddress",
      "smtp_server": "your domain's smtp server",
      "imap_server": "your domain's imap server",
      "port": 465
  }
}
```

- Gmail will _not_ work due to their security restrictions.
- it's very bad practice to store your password in plaintext; take appropriate precautions.

## Scheduling Reminder Emails

- type "crontab -e" in the terminal and add something like:
  - `0 4 * * * remind --generate` (sends matching reminders at 4AM)
  - `0 4 * * * remind --later` (sends emails scheduled for later)

- your setup may require `remind` to be replaced with something like:
  - `0 4 * * * python3 /path/to/site-packages/remind/remind.py --generate`

- this function requires use of SMTP; please ensure you've configured this correctly.

# Usage

- `remind`: Schedule a new reminder interactively
- `remind --title 'reminder title' --when 'june 20'`: Schedule a new reminder programatically
- `remind --title 'reminder title' --when '2024-06-20'`: Schedule a new reminder programatically
- `remind --title 'reminder title' --when 'every 3 weeks'`: Schedule a new reminder programatically
- `remind --title 'reminder title' --when 'friday'`: Schedule a new reminder programatically
- `remind --title 'reminder title' --when friday --save`: Schedule a new reminder programatically, saves without confirmation
- `remind --title 'reminder title' --when 'every 2 Mondays'`: Schedule a new reminder programatically
- `remind --title 'reminder title' --when 'now'`: Sends an email immediately
- `remind -h` (or `--help`): Displays usage information.
- `remind -g` (or `--generate`): Generates all reminders scheduled for today.
  - use `--dry-run` to see what would be sent without actually sending anything.
  - `remind -g --file=/path/to/special/remind.md` will use the specified file instead of the default.
  - I recommend setting up a crontab.
- `remind --later`: Emails reminders that are marked with `[later]`
- `remind --st` (or `--show-tomorrow`): Lists reminders in remind.md that target tomorrow's date
- `remind --sw` (or `--show-week`): Lists reminders for the next 7 days
- `remind -e` (or `--edit`): Opens `remind.md` in your configured editor
- `remind --list-all`: Lists all reminders in `remind.md`. Useful for debugging.
- `cabinet --config`: Configures [cabinet](https://pypi.org/project/cabinet/)

## Scheduling Reminders With TUI
- unless `--save` is used, a confirmation will appear.
- use arrow keys (or `j` and `k` in VI Mode) to navigate.
- arrow left and right to iterate through:
  - type
  - value
  - frequency
  - starting date ("Starts On")
  - offset

### VI Mode and Keybindings
- when the confirmation appears, use `j` or `k` to enter VI mode.
- `j` and `k` navigate up and down; `h` and `l` navigate left and right.
- use `i` to exit VI mode.
- use `q` to cancel the reminder.

## Scheduling Reminders With remind.md

- The `remind.md` file is a simple Markdown file that contains your reminders.
- Syntax: `[tag,frequency,offset]modifier Title`

### Tags
| Tag | Description |
| --- | --- |
| d   | day |
| w   | week |
| m   | month |
| YYYY-MM-DD   | date |
| MM-DD   | date |
| dom | day of month |
| sun | Sunday |
| mon | Monday |
| tue | Tuesday |
| wed | Wednesday |
| thu | Thursday |
| fri | Friday |
| sat | Saturday |
| later | for later |

### Frequency
- a number indicating how often the reminder should be sent (e.g., every 2 weeks, every 3 months, etc.)
- not valid for date or later tags

### Offset
- when scheduling a reminder, you can adjust the `offset` field to shift reminder schedules.
- For instance, one reminder may be "every 2 weeks", and the other can be every 2 weeks with an offset of 1, resulting in alternating reminders.

The offset is determined by the epoch date.
- The Epoch time is the number of seconds since January 1, 1970, UTC.
- For example, if the current time is `1619394350`, then today is Sunday, April 25, 2021 at 11:45:50PM UTC.
- The "week number" is calculated by `epochTime`/60/60/24/7.
  - `1619394350 /60/60/24/7 ~= 2677`
  - `2677 % 3 == 1`, meaning scheduling a reminder for `[W,3]` would be sent last week, but not this week (or next week or the week after).

### Modifiers
| Modifier | Description |
| --- | --- |
| d | delete after sending (one-time reminder) |
| c | execute title as command; do not send email |

### Good Examples
- These are some examples of how your remind.md file could look.

```markdown
[w,1] Laundry
- this will send each week on Sunday. 

[w,2] Sheets
- This will be sent every 2 weeks on Sunday.

[m,3] Review Budget # comments will be ignored in titles
- This will be sent on the 1st of every 3 months.

[m,3,2] Change AC filter
- every 3 months, with an offset of 2
(see notes about Offset below)

[2024-05-03]d send report
- send on May 3
- This will be deleted after it's sent, as indicated by `]d`.

[09-20,1] Get a Flu Shot
This will be sent on September 20.
Anything underneath a reminder tag is considered a note and will
be sent in the body of the email.

[fri] Submit Timesheet
<b>Will be sent every Friday. Reminder notes support HTML.</b>

[fri,2] Payday!
- This will send every other Friday.

[thu,1]c ls > /home/tyler/directory.log
- Reminders ending with `]c` will be executed as commands, rather than
sent as emails.

[d,1] 40 Daily Pushups
This is sent each day.

[later] play diplomacy board game
This isn't sent, but it is saved for later and can be sent using
`remind --later`.
```

# Contributing
- Contributions to RemindMail are welcome! Please feel free to fork the repository, make your changes, and submit a pull request.

# License
- RemindMail is released under the MIT license. For more details, see the LICENSE file in the repository.

# Disclaimer
- This is a non-commercial, open-source project; your data is your responsibility. Take appropriate precautions to shield sensitive information.
- I cannot be held responsible for any data loss or other issues that may arise from using this tool.

# Author Info
- Tyler Woodfin
- [https://tyler.cloud](https://tyler.cloud)
- [feedback-remindmail@tyler.cloud](mailto:feedback-remindmail@tyler.cloud)