# remindmail

- turns reminders written in terminal into emails; supports scheduled reminders

## features

- easily manage your To Do list from anywhere in the terminal
- schedule one-time or recurring reminders
- create issues for your Jira board
- schedule commands (your crontab can't run every 2 weeks as easily!)

# notable dependencies

- use `pip install -r requirements.md` to install all dependencies
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
  - in cabinet's `settings.json`, set the email information using the example below
    - note that Gmail will _not_ work due to their security restrictions.
    - it's very bad practice to store your password in plaintext; for this reason, never sync this file.
    - always use a unique email address specifically for this, and _especially_ use a unique password.
  - your settings.json file should look similar to this example:

  ```
  {
    "path": {
      "remindmail": {
        "local": "/home/pi/remindmail"
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

## scheduling reminder checks

- type "crontab -e" in the terminal

- add the line below (without the >, without the #, replacing the path with your real path):
  - `0 * * * * remind generate` (every hour, generate based on remind.md)

# usage

- `-h` (or `--help`): Displays usage information.
- `-ls` (or `-l` or `--list`): Lists all current reminders in `remind.md`.
- `-g` (or `--generate`): Generates all reminders scheduled for today. 
  - I recommend setting up a crontab (see [generate](##generate))
- `--later`: Emails reminders that are marked with `[any]`
- `--show-tomorrow`: Lists reminders in remind.md that target tomorrow's date
- `--show-week`: Lists reminders for the next 7 days
- `--sent-today`: Prints the number of reminders sent today (or yesterday, if before 4AM)
- `--stats`: Prints usage statistics about RemindMail
- `-o` (or `--offset`): Calculates the offset of a date (see [offset](##offset))
- `-e` (or `--edit`): Opens `remind.md` in vim
- `-j` (or `--jira`): Sends your reminder to a new Jira task for your desired board (see [Jira](#jira))

## Trello
- `-b` (or `--board`): An argument; the name of the Trello board to use
- `--list-name`: An argument; the name of the Trello list to use
- `-ti` (or `--trello-items`): Prints items within a Trello list (accepts `-b` or `--board`, `--list-name`)
  - If a board is not specified, the user is prompted to choose one
  - If a list is not specified, the user is prompted to choose one
- `-tl` (or `--trello-list`): Prints the lists within a Trello board (accepts `-b` or `--board`, `--list-name`)
  - If a board is not specified, the user is prompted to choose one
- `-ta` (or `--trello-add`): Adds an item to a Trello list (accepts `-b` or `--board`, `--list-name`, `--item-name`)
  - If a board is not specified, the user is prompted to choose one
  - If a list is not specified, the user is prompted to choose one
  - If an item is not specified, the user is prompted to enter one

## list (-l, -ls, or --list)
- lists all current reminders in `remind.md`

## generate (-g or --generate)
- generates reminders from `remind.md` that match the condition in brackets, 
such as `[wed]` matching if today is Wednesday

- it is highly recommended to schedule this in crontab (Linux, MacOS) by calling `crontab -e` and adding something like
```
# runs every hour at 5 minutes past the hour
5   * * * * python3 /path/to/site-packages/remind/remind.py -g
```

- reminders are generated only every 12 hours, but this can be overcome with `remind -g --force`
- to test your `remind.md` without actually sending reminders, use `remind -g --dry-run`

- this function requires use of SMTP; please ensure you've configured this correctly.

## later (--later)

- emails reminders in `remind.md` marked with `[any]`

## edit (-e or --edit)

- `remind edit` looks at the `path -> edit -> remind -> value` property in cabinet's settings.json:

```
{
    "path": {
      "edit": {
        "remind": {
          "value": "/fullpath/to/remind.md"
        }
      }
    }
  }
```

## offset (-o or --offset)

- `remind -o <type> <date (YYYY-MM-DD, optional)> <n>`
- (`type` is day, week, month)
- (`n` is 'every `n` days')

- Take the results of this function and use it to add an offset.

  - If you want something to happen every 3 days starting tomorrow, use:
  - `remind -o day <tomorrow's date YYYY-MM-DD> 3`

  - If the answer is 2, then you can add this to remind.md:
  - [D%3+2] Description here

### how this is calculated

- The Epoch time is the number of seconds since January 1, 1970, UTC.
- For example, if the current time is 1619394350, then today is Sunday, April 25, 2021 at 11:45:50PM UTC.
- The "week number" is calculated by {epochTime}/60/60/24/7.
  - 1619394350 /60/60/24/7 ~= 2677
  - 2677 % 3 == 1, meaning scheduling a reminder for [W%3] would be sent last week, but not this week (or next week or the week after).

### examples

- e.g. `remind -o day 2022-12-31 12`
- (find offset for every 12 days intersecting 2022-12-31)

- e.g. `remind -o week 2022-12-31 3`
- (every 3 weeks intersecting 2022-12-31)

- e.g. `remind -o month 2022-12-31 4`
- (every 4 months intersecting 2022-12-31)

- e.g. `remind -o day 5`

  - (every 5 days intersecting today)

- e.g. `remind -o week 6`

  - (every 6 weeks intersecting today)

- e.g. `remind -o month 7`
  - (every 7 months intersecting today)"""

# logging

- by defualt, remindmail's log path is set to `cabinet`'s default log
- otherwise, you can set `path -> remindmail -> log` in `cabinet` (see Setup above) for a custom directory.

# scheduling reminders with remind.md

- this file is the heart of this tool, used for scheduling one-time or recurring reminders.
- place the "good" example in the `remind.md example` section below in a file named `remind.md`.
- reminders from the `remind.md` file will be emailed once the conditions are met.

## using colons to edit email body

- any text after a colon (`:`) will be placed in the body of the email.

## using natural language to add to remind.md

- `remind me to take out the trash` will immediately send an email upon confirmation
- `remind to take out the trash tomorrow` will add `[YYYY-MM-DD]d take out the trash` upon confirmation (where `YYYY-MM-13` is the next day)
  - if it is before 3AM, the reminder will immediately send an email upon confirmation
- `remind write essay: need to go to library` will immediately send an email with the subject `write essay` and body `need to go to library` upon confirmation
- `remind me to take out the trash tomorrow` will add `[YYYY-MM-DD]d take out the trash` upon confirmation (where `YYYY-MM-DD` is tomorrow's date)
- `remind me take out the trash on Thursday` will add `[thu]d take out the trash` upon confirmation
- `remind to take out the trash on the 13th` will add `[YYYY-MM-13]d take out the trash` upon confirmation (where `YYYY-MM-13` is the next `13th`)
- `remind go to the gym in 4 months` will add `[YYYY-MM-DD]d take out the trash` upon confirmation (where `YYYY-MM-DD` is 4 months from today)
- `remind me spring is here in 6 weeks` will add `[YYYY-MM-DD]d spring is here` upon confirmation (where `YYYY-MM-DD` is 6 weeks from today)
- `remind me to finish procrastinating in 5 days` will add `[YYYY-MM-DD]d finish procrastinating` upon confirmation (where `YYYY-MM-DD` is 5 days from today)
- `remind me take out the trash every 2 weeks` will add `[W%2] take out the trash` upon confirmation
  - for recurring reminders, use `every n days`, `every n weeks`, or `every n months`
- try other combinations, and feel free to contribute to the codebase for other scenarios!

### parse without time

- some queries, like `remind me to buy 12 eggs` can be misinterpreted from the date parser library, and the confirmation may ask to schedule the reminder on the 12th of the month.
  - these edge cases aren't worth fixing, in the interest of preserving the ability for something like "remind me on the 12th to buy eggs" to continue working reliably.
  - in these situations, it's worth choosing `(p)arse without time`, which ignores any potential dates and asks to send the reminder immediately

## manually editing remind.md to schedule reminders

### days

```
[D%1]         This reminder is sent every day.
[D%4]         This reminder is sent every 4 days.

[mon]         This reminder is sent if today is Monday.
[Monday]      This reminder is sent if today is Monday.
[thu]         This reminder is sent if today is Thursday.
[Thursday]d   This reminder is sent, then deleted, if today is Thursday.
[D01]         This reminder is sent if today is the 1st of the month.
[D31]d        This reminder is sent, then deleted, if today is the 31st of the month.
[D31]c        cd /foo/bar && rm -rf / # this reminder is a scheduled command.

[3-5]         This reminder is sent if today is March 5.
[3/5]d        This reminder is sent, then deleted, if today is March 5.
[3/5]1        This reminder is sent, then deleted, if today is March 5.
[2022-3-5]d   This reminder is sent, then deleted, if today is March 5.
[2022-3-5]c   cd /foo/bar && rm -rf / # this reminder is a scheduled command.
```

### weeks

```
[W%3]         This reminder is sent if today is a Sunday of every third week, based on Epoch Time. See below...
[thu%2]       This reminder is sent every other Thursday.
[thu%2+1]     This reminder is sent every other Thursday (between the weeks of the line above).
[W%3+1]       This reminder is sent if today is a Sunday of every third week, _with an offset of 1_, meaning if [W%3] would normally be sent last week, it will be sent this week instead.
```

### months

```
[M%5]         This reminder is sent every 5 months (_not necessarily May and October! pay attention to offsets_)
[M%2]d        This reminder is sent at the next even-numbered month, then deleted.
[M%2]c        cd /foo/bar && rm -rf / # this reminder is a scheduled command.
```

### one-time or n-time reminders

```
[4/23]3       This reminder will be sent if today is April 23, then converted into [4/23]2
[4/23]2       This reminder will be sent if today is April 23, then converted into [4/23]1 (same as [4/23]d)
[4/23]1       This reminder is sent, then deleted, if today is April 23.
[4/23]d       This reminder is sent, then deleted, if today is April 23.

[M%3]6        This reminder will be sent, then decremented, every 3 months, until it becomes [M%3]1 in approximately 18 months.
[D%2]30       This reminder will be sent, then decremented, every other day, until it becomes [D%2]1 in approximately 2 months.
```

### "any time" reminders for later

```
[any]         This reminder requires manual removal from remind.md
[any]         You will be given a summary of [any] reminders when generateSummary() is called.
[any]         This can be called as `remind later`
```

It is recommended you add `remind later` as a scheduled crontab action.

### examples that won't work

```
[D50]         Months only have up to 31 days.
[D%3] d       The 'd' operator must be immediately next to the ] symbol.
[Y%5]         Year is unsupported.
(thu)         You must use brackets.
{thu}         You must use brackets.
   [W%3]      You must start reminders at the start of a newline.
[W%3-1]       This is invalid. To add an offset, you MUST use +.
[W%3+4]       An offset of 4 makes no sense and won't be triggered because [W%3+3] is the same thing as [W%3+0]. Use [W%3+1] instead.

```

## calculating and scheduling "every n weeks", "every n days", "every n months"

- see [offset](##offset)

## using "d" to set one-time reminders

- an item with `]d`, such as `[D%5]d`, will add the reminder and remove it from remind.md, meaning it will only generate once until you add it again.
  - this is useful for scheduling a reminder in the future that you don't need to repeat.

# Jira Integration

RemindMail provides a barebones integration with Jira to create issues directly from the application. To enable this integration, you need to configure the required Jira settings in the Cabinet configuration file.

## configuration

Before using the Jira integration, ensure that you have the following information available:

- Jira project URL: The base URL of your Jira project.
- Jira email: The email associated with your Jira account.
- Jira API token: The API token generated for your Jira account.
  - obtain through [these instructions](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- Jira project key: The key of the Jira project where you want to create issues.

Using [Cabinet](https://pypi.org/project/cabinet/), set the values by running:

```
cabinet --put jira email <your Jira email>
cabinet --put jira project-url <your project url, e.g. https://username.atlassian.net>
cabinet --put jira project-key <your project key prefix that all issues have, e.g. USR>
cabinet --put keys jira <your Jira API token>
```

Make sure to replace values in brackets with your own values.

## Usage

```
# creates a ticket (with prompts for description, label, issue type)
remind -m this is a new ticket --jira

# creates a ticket without prompts
remind --jira "this is a story 4" -t task --desc "Testing description" --label "testing"

# select '(j)' in confirmation menu
remind -m this is a new jira ticket
```

After the issue has been created, a success message and link to the new issue will appear.

## Trello Integration

## configuration

Before using the Trello integration, [obtain a Trello API Key](https://developer.atlassian.com/cloud/trello/guides/rest-api/authorization/).

Using [Cabinet](https://pypi.org/project/cabinet/), set the API key by running:

```
cabinet --put keys trello <api key here>
```

Upon first running a Trello-related command, you will be prompted to authorize your application in the browser.

## usage

```
# prints all lists in the `Shopping` board
remind -tl Shopping

# prints all items from a list (interactive)
remind -ti

# prints all items from the `Tyler` list in the `Shopping` board
remind -ti --board Shopping --list-name Tyler

# select '(j)' in confirmation menu
remind -m this is a new jira ticket
```