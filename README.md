# remindmail

- Turns reminders written in terminal into emails; integrates with Google Assistant; supports scheduled reminders

## features

- Easily manage your To Do list from anywhere in the terminal
- Schedule one-time or recurring reminders
- Automatically sync as a plaintext file with Dropbox, Google Drive, Nextcloud, or any other Cloud Storage provider using [rclone](https://rclone.org/install/)

# dependencies

- Linux (Raspberry Pis work great!)
- [securedata](https://github.com/tylerjwoodfin/securedata)
- Python3

# setup

- install Python3
- install [securedata](https://github.com/tylerjwoodfin/securedata)

  - Setup using `securedata config`; see securedata's README for complete setup instructions
  - Set the full directory path of your `remind.md` file using `path -> remindmail -> local`, like this example SecureData `settings.json` file:

  ```
  {
    "path": {
      "remindmail": {
        "local": "/home/pi/remindmail"
      }
    }
  }
  ```

- follow the `remind.md` section below

## syncing with rclone (optional)

- complete the steps above in "Setup"
- install [rclone](https://rclone.org/install/).
- run `rclone config` to set up a cloud storage provider of your choice
- set the full directory path of your cloud using `securedata`; set `path -> remindmail -> cloud` (see `Setup` for an example)

## scheduling reminder checks:

- type "crontab -e" in the terminal

- add the line below (without the >, without the #, replacing the path with your real path):
  - `0 * * * * python3 path/to/main.py generate`

# logging

- by defualt, activity is logged to `/var/log/remindmail.log`
- otherwise, you can set `path -> remindmail -> log` in `securedata` (see Setup above) for a custom directory.

# remind.md

- this file is the heart of this tool, used for scheduling one-time or recurring reminders.
- place the "good" example in the `remind.md example` section below in a file named `remind.md`.
- reminders from the `remind.md` file will be emailed once the conditions are met.

## important notes

- capitalization doesn't matter anywhere. Feel free to use "[d01]" or "[12-31]D" or "[wEd]".
- % operators are based on Epoch Time, not a specific year/month. If you use "[M%5]", it adds _every 5 months_, not necessarily May or October. This is why offsets are necessary to "align" it properly.
- see the other sections below to further understand the + operator

## remind.md examples

### good

```
[mon]     This reminder is added if today is Monday.
[thu]     This reminder is added if today is Thursday.
[D01]     This reminder is added if today is the 1st of the month.
[D31]     This reminder is added if today is the 31st of the month.
[12-31]   This reminder is added if today is December 31.
[1-5]     This reminder is added if today is January 5. (not tested on non-US systems)
[M%5]     This reminder is generated every 5 months (*not necessarily May and October! pay attention to offsets*)
[W%3]     This reminder is added if today is a Sunday of every third week, based on Epoch Time. See instructions below...
[D%4]     This reminder is added every 4 days.
[thu%2]   This reminder is added every other Thursday.
[thu%2+1] This reminder is added every *other* other Thursday.
[W%3+1]   This reminder is added if today is a Sunday of every third week, _with an offset of 1_, meaning if [W%3] would normally be added last week, it will be added this week instead.
[M%2]d    This reminder is added at the next even-numbered month, then deleted from remind.md.

[M%6+3]d  Schedule a doctor's appointment
[W%1+5]   Take the trash out each Thursday
[D%1]     Go to bed
[12-31]d  Celebrate the next New Year's Eve, then delete the reminder
[M%4]     Spend 15 minutes away from your computer every 4 months
```

### bad

```
[Monday]  You must use sun, mon, tue, wed, thu, fri, or sat. Capitalization doesn't matter.
[D50]     Months only have up to 31 days.
[D%3] d   The 'd' operator must be immediately next to the ] symbol.
[Y%5]     Year is unsupported.
(thu)     You must use brackets.
{thu}     You must use brackets.
  [W%3]   You must start reminders on the first column.
[W%3-1]   This is invalid. To add an offset, you MUST use +.
[W%3+4]   An offset of 4 makes no sense because [W%3+3] is the same thing as [W%3+0], so [W%3+4] is the same as [W%3+1]. Use [W%3+1] instead.
```

## using % to set "every n weeks", "every n days", "every n months":

- The Epoch time is the number of seconds since January 1, 1970, UTC.
- For example, if the current time is 1619394350, then today is Sunday, April 25, 2021 at 11:45:50PM UTC.
- The "week number" is calculated by {epochTime}/60/60/24/7.
  - 1619394350 /60/60/24/7 ~= 2677
  - 2677 % 3 == 1, meaning scheduling a reminder for [W%3] would be added last week, but not this week (or next week or the week after).

### calculating and scheduling offsets

- `remindmail offset <type> <date (YYYY-MM-DD, optional)> <n>`
- (`type` is day, week, month)
- (`n` is 'every `n` days')

- Take the results of this function and use it to add an offset to a function.

  - If you want something to happen every 3 days starting tomorrow, use:
  - remindmail offset day <tomorrow's date YYYY-MM-DD> 3

  - If the answer is 2, then you can add this to remind.md:
  - [D%3+2] Description here

  - e.g. `remindmail offset day 2022-12-31 12`
  - (find offset for every 12 days intersecting 2022-12-31)

  - e.g. `remindmail offset week 2022-12-31 3`
  - (every 3 weeks intersecting 2022-12-31)

  - e.g. `remindmail offset month 2022-12-31 4`
  - (every 4 months intersecting 2022-12-31)

  - e.g. `remindmail offset day 5`

    - (every 5 days intersecting today)

  - e.g. `remindmail offset week 6`

    - (every 6 weeks intersecting today)

  - e.g. `remindmail offset month 7`
    - (every 7 months intersecting today)"""

## using "d" to set one-time reminders:

- an item with `]d`, such as `[D%5]d`, will add the reminder and remove it from remind.md, meaning it will only generate once until you add it again.
  - this is useful for scheduling a reminder in the future that you don't need to repeat.

# credit

- Google polling forked from [https://github.com/jonahar/google-reminders-cli](https://github.com/jonahar/google-reminders-cli)
