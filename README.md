# RemindMail: Reminder Management Tool
A powerful CLI designed to help you schedule and organize reminders efficiently and effectively. 
Easily manage your To Do list, schedule one-time or recurring reminders, add notes, and view and manage upcoming reminders, all from the comfort of your terminal.

## Table of Contents
- [RemindMail: Reminder Management Tool](#remindmail-reminder-management-tool)
  - [Table of Contents](#table-of-contents)
- [✨ New in 3.0.0:](#-new-in-300)
- [Features](#features)
- [Dependencies](#dependencies)
- [Installation and Setup](#installation-and-setup)
  - [Full Install (recommended)](#full-install-recommended)
  - [Minimal Install (experimental)](#minimal-install-experimental)
  - [Cabinet Configuration](#cabinet-configuration)
    - [MongoDB Configuration](#mongodb-configuration)
  - [Scheduling Reminder Emails](#scheduling-reminder-emails)
- [Usage](#usage)
  - [Scheduling Reminders With TUI](#scheduling-reminders-with-tui)
    - [VI Mode and Keybindings](#vi-mode-and-keybindings)
  - [Scheduling Reminders With remindmail.yml](#scheduling-reminders-with-remindmailyml)
    - [YAML Key Reference](#yaml-key-reference)
      - [`name`](#name)
      - [`every`](#every)
      - [`unit`](#unit)
      - [`offset`](#offset)
      - [`day`](#day)
      - [`dom`](#dom)
      - [`date`](#date)
      - [`later`](#later)
      - [`delete`](#delete)
      - [`notes`](#notes)
      - [`command`](#command)
      - [`email`](#email)
      - [`tags`](#tags)
    - [Good Examples](#good-examples)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)
- [Author Info](#author-info)

# ✨ New in 3.0.0:
- Migrated from a custom `.md` file to a YAML file
  - Allows for easier extensibility in future releases
- Added optional tags for more flexible scheduling
- Better handling for errors and edge case
- Improved TUI for delete and command options

# Features
RemindMail offers a variety of features to enhance your productivity:

- Easily manage your To Do list from anywhere in the terminal
- Send one-time or recurring reminders to your inbox
- Add notes or "for later" reminders
- View and manage upcoming reminders
- Organize reminders with tags for better filtering

# Dependencies
- `zsh` or `bash`
- `python3`
- [cabinet](https://pypi.org/project/cabinet/)
  - used to store the `remindmail.yml` path and other important variables
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
    "mongodb_enabled": true, # optional if using mongodb - default false
    "subject_prefix": "Reminder ", # optional - custom prefix for email subjects (default: "📌 ")
    "path": {
        "file": "/path/to/remindmail.yml"
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

### MongoDB Configuration
- MongoDB is used to log reminders when `mongodb_enabled` is set to `true`.
- This is configured via the Cabinet configuration in `~/.config/cabinet/config.json` - see [https://www.github.com/tyjerwoodfin/cabinet](https://www.github.com/tyjerwoodfin/cabinet) for configuration instructions.

## Scheduling Reminder Emails

- type "crontab -e" in the terminal and add something like:
  - `0 4 * * * remind --generate` (sends matching reminders at 4AM)
  - `0 4 * * * remind --later` (sends emails scheduled for later)

- your setup may require `remind` to be replaced with something like:
  - `0 4 * * * python3 /path/to/site-packages/remind/remind.py --generate`

- this function requires use of SMTP through Cabinet; please ensure you've configured this correctly.

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
  - `remind -g --file=/path/to/special/remindmail.yml` will use the specified file instead of the default.
  - I recommend setting up a crontab.
- `remind --later`: Emails reminders that are marked with `[later]`
- `remind --st` (or `--show-tomorrow`): Lists reminders in remindmail.yml that target tomorrow's date
- `remind --sw` (or `--show-week`): Lists reminders for the next 7 days
- `remind -e` (or `--edit`): Opens `remindmail.yml` in your configured editor
- `remind --list-all`: Lists all reminders in `remindmail.yml`. Useful for debugging.
- `remind --find 'search text'`: Displays reminders containing the given text in title, date, or day fields.
  - Text search examples: `remind --find laundry`, `remind --find monday`
  - Date search examples: `remind --find 2025-04-24`, `remind --find 04/24`
  - If search text is a valid date, displays reminders that would send on that date.
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

## Scheduling Reminders With remindmail.yml

- The `remindmail.yml` file is a YAML configuration file that contains your reminders.
- Each reminder is defined as an object under the `reminders` key.

### YAML Key Reference

#### `name`
- **Type:** `string`
- **Description:** The description or title of the reminder.

#### `every`
- **Type:** `int`
- **Description:** How often the reminder recurs (e.g. every `2` units of time).
- **Default unit:** `days` (unless `unit` is specified).

#### `unit`
- **Type:** `string` (`days`, `weeks`, `months`)
- **Description:** Time unit for `every`. Only needed for non-day intervals.

#### `offset`
- **Type:** `int`
- **Description:** Delay (in same units as `every`) before the first occurrence.

#### `day`
- **Type:** `string` (`mon`, `tue`, ..., `sun`)
- **Description:** Specifies a day of the week for weekly reminders.

#### `dom`
- **Type:** `int` (1–31)
- **Description:** Day of the month when the reminder occurs.

#### `date`
- **Type:** `string` (`YYYY-MM-DD` or `MM-DD`)
- **Description:** A specific one-time or annual date for the reminder.

#### `later`
- **Type:** `bool`
- **Description:** Marks the reminder as unscheduled or saved for later.

#### `delete`
- **Type:** `bool`
- **Description:** If `true`, the reminder should be deleted after it's triggered.

#### `notes`
- **Type:** `string`
- **Description:** If set, sends within the body of the email and marks the subject with 📝. Basic HTML is supported.

#### `command`
- **Type:** `string`
- **Description:** If set, runs the command and outputs the results to the body of the email.

#### `email`
- **Type:** `string`
- **Description:** Optional email address to send this specific reminder to. If not set, uses the default email configured in Cabinet's `email -> to` setting.

#### `tags`
Optional list of tags to categorize and filter reminders. Tags can be used to group related reminders and filter which reminders are sent when using the `--generate` command.

Example:
```yaml
reminders:
  - name: "Weekly team meeting"
    day: "mon"
    tags: ["work", "meeting"]
    notes: "Don't forget to prepare the agenda"
    
  - name: "Grocery shopping"
    every: 7
    tags: ["personal", "shopping"]
    notes: "Buy milk and eggs"
```

You can then filter reminders by tags when generating:
```bash
remindmail --generate --tags work,meeting  # Only sends reminders with work or meeting tags
remindmail --generate --tags personal      # Only sends reminders with personal tag
remindmail --generate                      # Sends all reminders (default behavior)
```

Tags can be specified by a string or list in the YAML file:
```yaml
tags: "meeting"
```
or
```yaml
tags: ["work", "meeting"]
```

### Good Examples
Here are some examples of how your remindmail.yml file could look:

```yaml
reminders:
  - name: Workout and Stretch
    day: mon,wed,fri
    delete: false
  - name: Try Cursor IDE
    date: 2025-03-31
    delete: true
    notes: This will be <u>VERY</u> useful! <b>WOW</b>
  - name: Laundry and Sheets
    every: 6
    offset: 5
    delete: false
  - name: Monthly Budget
    unit: months
  - name: Change Toothbrush Head
    every: 3
    unit: months
    offset: 2
    delete: false
  - name: Try Umbrell OS
    later: true
  - name: Update Team Spreadsheet
    day: wed
    every: 2
    offset: 1
  - name: Homework File Count
    day: fri
    command: find ~/homework -maxdepth 1 -type f | wc -l
    notes: This is how many files are in ~/homework.
  - name: Send to spouse
    date: 2025-11-15
    email: spouse@protonmail.com
    notes: This reminder will be sent to a different email address
    
```

⚠️ Comments and extraneous spacing will NOT be saved after reminders are generated.

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