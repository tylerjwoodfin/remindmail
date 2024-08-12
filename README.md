# RemindMail: Reminder Management Tool
Welcome to RemindMail, a powerful CLI tool designed to help you schedule and organize reminders efficiently. This utility leverages natural language for setting reminder times and includes functionalities to view, generate, and manage reminders directly from your terminal.

## features
RemindMail offers a variety of features to enhance your productivity:

- Easily manage your To Do list from anywhere in the terminal
- Schedule one-time or recurring reminders to your inbox
- Add notes or "for later" reminders
- View and manage upcoming reminders

# notable dependencies

- Linux (Raspberry Pis work great!)
- [cabinet](https://pypi.org/project/cabinet/)
  - used to store JSON data; specifically, used to store the `remind.md` path and other important variables
- a unique, non-Gmail address specifically for this project
  - do not use an email address that you use in other areas of your life
  - do not re-use a password you've used anywhere else; use a unique password.
- Python3

# setup

```bash
  python3 -m pip install remindmail

  # adjust path accordingly
  pip install -r /path/to/requirements.md

  cabinet config # cabinet must be configured properly
```

## cabinet config
- you need to install and configure [cabinet](https://github.com/tylerjwoodfin/cabinet)

  - initialize using `cabinet config`; see cabinet's README for details

  ```bash
  cabinet -p path remindmail file </path/to/remind.md>
  cabinet -p email from <your unique and non-Gmail email address>
  cabinet -p email from_name <your name (can be anything)>
  cabinet -p from_pw <your email password>
  cabinet -p email to <where reminder will send to>
  cabinet -p email smtp_server <your SMTP server>
  cabinet -p email port <your email port>
  cabinet -p email imap_server <your IMAP server>
  ```
  - note that Gmail will _not_ work due to their security restrictions.
  - it's very bad practice to store your password in plaintext; for this reason, never sync this file.
  - always use a unique email address specifically for this, and _especially_ use a unique password.

  - example below:
  ```
  {
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

## scheduling reminder checks

- type "crontab -e" in the terminal and add something like:
  - `0 4 * * * remind --generate` (sends matching reminders at 4AM)
  - `0 4 * * * remind --later` (sends emails scheduled for later)

- your setup may require `remind` to be replaced with something like:
  - `0 4 * * * python3 /path/to/site-packages/remind/remind.py --generate`

- this function requires use of SMTP; please ensure you've configured this correctly.

# usage

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
  - I recommend setting up a crontab.
- `remind --later`: Emails reminders that are marked with `[later]`
- `remind --st` (or `--show-tomorrow`): Lists reminders in remind.md that target tomorrow's date
- `remind --sw` (or `--show-week`): Lists reminders for the next 7 days
- `remind -e` (or `--edit`): Opens `remind.md` in your configured editor
- `cabinet --config`: Configures [cabinet](https://pypi.org/project/cabinet/)

## using the TUI to confirm reminders
- unless `--save` is used, a confirmation will appear.
- use arrow keys (or `j` and `k` in VI Mode) to navigate.
- arrow left and right to iterate through:
  - type
  - value
  - frequency
  - offset

### VI Mode and Keybindings
- when the confirmation appears, use `j` or `k` to enter VI mode.
- `j` and `k` navigate up and down; `h` and `l` navigate left and right.
- use `i` to exit VI mode.
- use `q` to cancel the reminder.

## some notes about offset

- when scheduling a reminder, you can adjust the `offset` field to shift reminder schedules.
- For instance, one reminder may be "every 2 weeks", and the other can be every 2 weeks with an offset of 1, resulting in alternating reminders.

The offset is determined by the epoch date.
- The Epoch time is the number of seconds since January 1, 1970, UTC.
- For example, if the current time is 1619394350, then today is Sunday, April 25, 2021 at 11:45:50PM UTC.
- The "week number" is calculated by {epochTime}/60/60/24/7.
  - 1619394350 /60/60/24/7 ~= 2677
  - 2677 % 3 == 1, meaning scheduling a reminder for [W,3] would be sent last week, but not this week (or next week or the week after).

## remind.md

These are some examples of how your remind.md file will look.

## good examples
[w,1] Laundry
- this will send each week on Sunday. 

[w,2] Sheets
- This will be sent every 2 weeks on Sunday.

[m,3] Review Budget
- This will be sent on the 1st of every 3 months.

[m,3,2] Change AC filter
- every 3 months, with an offset of 2
(see notes about Offset below)

[2024-05-03]d send report
- send on May 3
- This will be deleted after it's sent, as indicated by `]d`.

[09-20,1] Get a Flu Shot
This will be sent on September 20.
By the way, anything underneath a reminder tag is considered a note and will
be sent in the body of the email.

[dow,fri] Submit Timesheet
<b>Will be sent every Friday. Reminder notes support HTML.</b>

[dow,fri,2] Payday!
- This will send every other Friday.

[dow,thu,1]c ls > /home/tyler/directory.log
- Reminders ending with `]c` will be executed as commands, rather than
sent as emails.

[d,1] 40 Daily Pushups
This is sent each day.

[later] play diplomacy board game
This isn't sent, but it is saved for later and can be sent using
`remind --later`.

# Contributing
Contributions to RemindMail are welcome! Please feel free to fork the repository, make your changes, and submit a pull request.

# License
RemindMail is released under the MIT license. For more details, see the LICENSE file in the repository.

# Author Info
Tyler Woodfin
https://tyler.cloud
feedback-remindmail@tyler.cloud