# remindmail

- turns reminders written in terminal into emails; integrates with Google Assistant; supports scheduled reminders

## features

- easily manage your To Do list from anywhere in the terminal
- schedule one-time or recurring reminders
- automatically sync scheduled reminders as a plaintext file with Dropbox, Google Drive, Nextcloud, or any other Cloud Storage provider using [rclone](https://rclone.org/install/)

# dependencies

- Linux (Raspberry Pis work great!)
- [securedata](https://github.com/tylerjwoodfin/securedata)
- a unique, non-Gmail address specifically for this project
  - do not use an email address that you use in other areas of your life
  - do not re-use a password you've used anywhere else; use a unique password.
- Python3

# setup

```bash
  python3 -m pip install remindmail
```

- you also need to install and configure [securedata](https://github.com/tylerjwoodfin/securedata)

  - initialize using `securedata config`; see securedata's README for complete setup instructions
  - in securedata's `settings.json`, set the full directory path of your `remind.md` file using `path -> remindmail -> local`
  - in securedata's `settings.json`, set the email information using the example below
    - note that Gmail will _not_ work due to their security restrictions.
    - it's very bad practice to store your password in plaintext; for this reason, never sync this file.
    - always use a unique email address specifically for this, and _especially_ use a unique password.
  - Your settings.json file should look similar to this example:

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

## pulling reminders from Google (optional)

- [Create a new Google Developer project](https://console.developers.google.com)

  - Create a new project
  - Select "Enable APIs and Services"
  - Search for "Calendar"
  - Enable Google Calendar API
  - Create an OAuth 2.0 Client ID:

    - For "type", use "desktop"
    - For detailed instructions, see [here](https://developers.google.com/identity/protocols/oauth2)

  - Find the client ID and client secret, then populate `settings.json` to match this example:

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
    },
    "remindmail": {
      "client_id": "Your client ID",
      "client_secret": "Your client secret"
    }
  }
  ```

  - Run `remind pull`; the terminal should prompt you to visit a link.
  - Visit the link, sign in, then copy the verification code into the terminal

- add to crontab:
  - `*/5 * * * * remind pull` (every 5 minutes, query Google for new reminders)

## syncing with rclone (optional)

- complete the steps above in "Setup"
- install [rclone](https://rclone.org/install/).
- run `rclone config` to set up a cloud storage provider of your choice
- set the full directory path of your cloud using `securedata`; set `path -> remindmail -> cloud` (see `Setup` for an example)

## scheduling reminder checks

- type "crontab -e" in the terminal

- add the line below (without the >, without the #, replacing the path with your real path):
  - `0 * * * * remind generate` (every hour, generate based on remind.md)

# usage

- natural language, e.g. `remind me to take the trash out on thursday`
- scheduling `remindmail pull` to automatically pull reminders from Google through crontab (see below)
- scheduling `remindmail generate` to automatically send emails based on date match from `remind.md` (see below)

# generate

- `remind generate` generates reminders from `remind.md` (see below)

# pull

- `remind pull` generates reminders from Google (see above)

# edit

- `remind edit` looks at the `path -> edit -> remind -> value` property in securedata's settings.json:

```
{
    "path": {
      "edit": {
        "remind": {
          "value": "/fullpath/to/remind.md",
          "sync": false
        }
      }
    }
  }
```

- Change `sync` to `true` to enable cloud syncing. This is disabled by default.

# logging

- by defualt, remindmail's log path is set to `securedata`'s default log
- otherwise, you can set `path -> remindmail -> log` in `securedata` (see Setup above) for a custom directory.

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

[3-5]         This reminder is sent if today is March 5.
[3/5]d        This reminder is sent, then deleted, if today is March 5.
[3/5]1        This reminder is sent, then deleted, if today is March 5.
[2022-3-5]d   This reminder is sent, then deleted, if today is March 5.
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
   [W%3]      You must start reminders on the first column.
[W%3-1]       This is invalid. To add an offset, you MUST use +.
[W%3+4]       An offset of 4 makes no sense and won't be triggered because [W%3+3] is the same thing as [W%3+0]. Use [W%3+1] instead.

```

## calculating and scheduling "every n weeks", "every n days", "every n months"

- `remind offset <type> <date (YYYY-MM-DD, optional)> <n>`
- (`type` is day, week, month)
- (`n` is 'every `n` days')

- Take the results of this function and use it to add an offset.

  - If you want something to happen every 3 days starting tomorrow, use:
  - `remind offset day <tomorrow's date YYYY-MM-DD> 3`

  - If the answer is 2, then you can add this to remind.md:
  - [D%3+2] Description here

### how this is calculated

- The Epoch time is the number of seconds since January 1, 1970, UTC.
- For example, if the current time is 1619394350, then today is Sunday, April 25, 2021 at 11:45:50PM UTC.
- The "week number" is calculated by {epochTime}/60/60/24/7.
  - 1619394350 /60/60/24/7 ~= 2677
  - 2677 % 3 == 1, meaning scheduling a reminder for [W%3] would be sent last week, but not this week (or next week or the week after).

## offset examples

- e.g. `remind offset day 2022-12-31 12`
- (find offset for every 12 days intersecting 2022-12-31)

- e.g. `remind offset week 2022-12-31 3`
- (every 3 weeks intersecting 2022-12-31)

- e.g. `remind offset month 2022-12-31 4`
- (every 4 months intersecting 2022-12-31)

- e.g. `remind offset day 5`

  - (every 5 days intersecting today)

- e.g. `remind offset week 6`

  - (every 6 weeks intersecting today)

- e.g. `remind offset month 7`
  - (every 7 months intersecting today)"""

## using "d" to set one-time reminders

- an item with `]d`, such as `[D%5]d`, will add the reminder and remove it from remind.md, meaning it will only generate once until you add it again.
  - this is useful for scheduling a reminder in the future that you don't need to repeat.

# credit

- Google polling forked from [https://github.com/jonahar/google-reminders-cli](https://github.com/jonahar/google-reminders-cli)
