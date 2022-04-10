from logging import exception
import client
import os
import sys
import re
from datetime import datetime
from subprocess import call
import time
from securedata import securedata, mail


today = datetime.today()
path_local = securedata.getItem(
    'path', 'remindmail', 'local')
path_cloud = securedata.getItem(
    'path', 'remindmail', 'cloud')
cloud_enabled = path_local and path_cloud
helpText = f"""\nUsage: remindmail <command>\n\n<command>:
	pull
    generate force
	config local <localPath>
	config cloud
	config cloudpath
	offset
	
	For help with a specific command: remindmail help <command>
	
Parameters (in brackets):
	taskInfo: enter any task you want to complete. Enclose in quotes, e.g. remindmail add 'take the trash out'
	localPath: Currently {path_local}. Settings are stored in {securedata.getConfigItem('path_securedata')} and should be stored as a JSON object (path -> remindmail -> local).

Notes Directory:
	Tasks.md and remind.md in {path_local}. Change the path by running "remindmail config notes <fullPath>" (stored in {securedata.getConfigItem('path_securedata')})

remind.md:
	when generate() is run (from crontab or similar task scheduler; not intended to be run directly), matching tasks are emailed.
	See the provided example remind.md in ReadMe.
	
	"""


def __monthsSinceEpoch(epoch):
    epochTime = time.localtime(epoch)
    return ((epochTime.tm_year - 1970) * 12) + epochTime.tm_mon


def __getWeekday(dayw):
    if dayw == 'sun':
        return 'Sunday'
    if dayw == 'mon':
        return 'Monday'
    if dayw == 'tue':
        return 'Tuesday'
    if dayw == 'wed':
        return 'Wednesday'
    if dayw == 'thu':
        return 'Thursday'
    if dayw == 'fri':
        return 'Friday'
    if dayw == 'sat':
        return 'Saturday'


def log(str, level="info"):
    path = securedata.getItem("path", "remindmail", "log") or securedata.setItem("path", "remindmail", "log",
                                                                                 securedata.getItem("path_log"))

    securedata.log(str, level=level, filePath=path)
    return


"""
Generates tasks from the remind.md file in {path_local}.
Intended to be run from crontab (try 'remindmail generate force' to run immediately)
"""


def generate():
    dayOfMonthTasksGenerated = str(
        securedata.getItem("remindmail", "day_generated"))

    dayOfMonthTasksGenerated = dayOfMonthTasksGenerated if dayOfMonthTasksGenerated != '' else 0

    if (str(datetime.today().day) != dayOfMonthTasksGenerated and datetime.today().hour > 0) or (len(sys.argv) > 2 and sys.argv[2] == "force"):
        log("Generating tasks")

        epochDay = int(time.time()/60/60/24)
        epochWeek = int(time.time()/60/60/24/7)
        epochMonth = int(datetime.today().month)

        dayOfMonthEnclosed = "[d{:02d}]".format(today.day)
        dayOfWeekEnclosed = f"[{today.strftime('%a').lower()}]"
        dateMMdashDDEnclosed = f"[{today.strftime('%m-%d')}]"

        try:
            remindMdFile = securedata.getFileAsArray(
                "remind.md", "notes")
        except exception as e:
            log(
                "Could not read remind.md; Aborting", level="error")
            sys.exit("Could not read remind.md; Aborting")

        for item in remindMdFile:
            if item.startswith(dayOfMonthEnclosed.lower()) or item.startswith(dayOfWeekEnclosed) or item.startswith(dateMMdashDDEnclosed):
                mail.send(f"Reminder - {item.split(' ', 1)[1]}", "")

                # handle deletion
                if "]d" in item:
                    log(f"Deleting item from remind.md: {item}")
                    remindMdFile.remove(item)

            elif item.startswith("[") and ("%" in item) and ("]" in item):

                if item[1:4] in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']:
                    splitType = item[1:4]
                else:
                    splitType = item[1].lower()  # d, w, m
                splitFactor = item.split("%")[1].split("]")[0]
                splitOffset = 0

                # e.g. [D%4+1] for every 4 days, offset 1
                if "+" in splitFactor:
                    splitOffset = int(splitFactor.split("+")[1])
                    splitFactor = int(splitFactor.split("+")[0])
                else:
                    splitFactor = int(splitFactor)

                try:
                    if splitType == "d":
                        if epochDay % splitFactor == splitOffset:
                            print(f"Sending: {item}")
                            mail.send(
                                f"Reminder - {item.split(' ', 1)[1]}", "")
                    elif splitType == "w":
                        if datetime.today().strftime("%a") == 'Sun' and epochWeek % splitFactor == splitOffset:
                            print(f"Sending: {item}")
                            mail.send(
                                f"Reminder - {item.split(' ', 1)[1]}", "")
                    elif splitType == "m":
                        if datetime.today().day == 1 and epochMonth % splitFactor == splitOffset:
                            print(f"Sending: {item}")
                            mail.send(
                                f"Reminder - {item.split(' ', 1)[1]}", "")
                    elif splitType in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']:
                        if datetime.today().strftime("%a").lower() == splitType and epochWeek % splitFactor == splitOffset:
                            print(f"Sending: {item}")
                            mail.send(
                                f"Reminder - {item.split(' ', 1)[1]}", "")
                except Exception as e:
                    log(
                        f"Could not send reminder from remind.md: {e}", level="error")

                # handle deletion
                if "]d" in item:
                    log(f"Deleting item from remind.md: {item}")
                    remindMdFile.remove(item)

        try:
            securedata.writeFile("remind.md", "notes",
                                 '\n'.join(remindMdFile))
            securedata.setItem("remindmail", "day_generated",
                               datetime.today().day)
        except exception as e:
            log("Could not rewrite remind.md", level="error")
        log("Generated tasks")
    else:
        print(f"Reminders have already been generated in the past 12 hours.")


"""
Prints help information returned by passing 'help' as a string into other functions.
"""


def help():
    if len(sys.argv) > 2:
        func = params.get(sys.argv[2])
        if hasattr(func, '__name__'):
            print(func("help"))
    else:
        print(helpText)


"""
Pulls reminders from Google, deletes them, and emails them to the address using the email in securedata (see README)
"""


def pull(s=None):
    if s == "help":
        return f"Pulls reminders from Google, deletes them, and adds them to Tasks.md in path_local (currently {path_local})"

    print("Pulling from Google...")

    cli = client.RemindersClient()

    try:
        items = cli.list_reminders(5)
    except Exception as e:
        log(
            f"Could not pull reminders from Google: {e}", level="warn")
        sys.exit(-1)

    # pull remind.md from cloud
    if cloud_enabled:
        os.system(
            f"rclone copy {path_cloud} {path_local}")

    # for each reminder, either add it to remind.md if > 1 day from now, or send an email now, then delete it
    for item in items:
        seconds_until_target = (
            item['target_date'] - datetime.now()).total_seconds()

        if seconds_until_target >= 86400 and not item["done"]:
            print(
                f"Moving {item['title']} to {path_local}/remind.md")

            try:
                with open(f"{path_local}/remind.md", 'a') as f:
                    f.write(f"\n{item['title']}")
            except Exception as e:
                log(
                    f"Could not write to remind.md: {e}", level="critical")
                sys.exit(-1)
        else:
            try:
                mail.send(f"Reminder - {item['title'].split(']d ')[1]}", "")
            except Exception as e:
                try:
                    mail.send(f"Reminder - {item['title']}", "")
                except Exception as e:
                    log(
                        f"Could not send reminder email: {e}", level="warn")

        # delete
        if cli.delete_reminder(reminder_id=item['id']):
            log(
                f"Pulled and deleted {item['title']} from Google Reminders")
        else:
            log(
                f"Could not delete {item['title']} from Google Reminders", level="warning")

    # sync possibly-modified remind.md
    if cloud_enabled:
        os.system(
            f"rclone sync {path_local} {path_cloud}")

    print("Pull complete.")


"""
An interactive way to set securedata variables. May be removed in a future updatetime.

Parameters:
- s: string; currently unused. Passing 'help' will only return the help information for this function.
"""


def config(s=None):
    if s == "help":
        return f"""remindmail config local <path>: Set your notes path (use full paths)
		e.g. remindmail config notes /home/userdir/Dropbox/Notes
		(this is stored SecureData; see README)
		
		remindmail config cloud: Set your cloud storage provider based on your rclone config (must have rclone- see ReadMe)
		e.g. remindmail config cloud
		(this is stored SecureData; see README)
		
		remindmail config cloudpath <path>: Set the path in your cloud service to store Tasks.md
		e.g., if you keep Tasks in Dropbox at Documents/Notes/Tasks.md: remindmail config cloudpath Documents/Notes
		(this is stored SecureData; see README)"""
    if len(sys.argv) < 3:
        print(config("help"))
        return

    if sys.argv[2].lower() == "local":
        newDir = sys.argv[3] if sys.argv[3][-1] == '/' else sys.argv[3] + '/'
        securedata.setItem("path", "remindmail", "local", newDir)
        print(
            f"remind.md should now be stored in {newDir}.")

    if sys.argv[2].lower() == "cloud":
        newDir = sys.argv[3] if sys.argv[3][-1] == '/' else sys.argv[3] + '/'
        securedata.setItem("path", "remindmail", "cloud", newDir)
        print(
            f"remind.md should now be synced in rclone through {newDir}.")


"""
Calculates the offset for a certain date (today by default)

Parameters:
- s: string; currently unused. Passing 'help' will only return the help information for this function.
"""


def offset(s=None):
    if s == "help":
        return f"""Calculates the offset for a certain date (today by default)

		remindmail offset <type> <date (YYYY-MM-DD, optional)> <n>
		(type is day, week, month)
		(n is 'every n days')

		Take the results of this function and use it to add an offset to a function.
		If you want something to happen every 3 days starting tomorrow, use:
		remindmail offset day <tomorrow's date YYYY-MM-DD> 3

		If the answer is 2, then you can add this to remind.md:
		[D%3+2] Task here
		
		e.g. remindmail offset day 2022-12-31 12
		(find offset for every 12 days intersecting 2022-12-31)

		e.g. remindmail offset week 2022-12-31 3
		(every 3 weeks intersecting 2022-12-31)

		e.g. remindmail offset month 2022-12-31 4
		(every 4 months intersecting 2022-12-31)

		e.g. remindmail offset day 2022-12-31 5
		e.g. remindmail offset week 2022-12-31 6
		e.g. remindmail offset month 2022-12-31 7"""

    if len(sys.argv) < 4:
        print("Usage: remindmail offset <type (day,week,month)> <date (optional, YYYY-MM-DD)> <n, as in 'every n <type>'>\nExample: remindmail offset week 2021-05-20 2\nFor help: 'remindmail help offset'")
        return

    if len(sys.argv) > 4:
        epochTime = int(datetime.strptime(sys.argv[3], "%Y-%m-%d").timestamp())
        offsetN = sys.argv[4]
    else:
        offsetN = sys.argv[-1]
        epochTime = int(time.time())

    try:
        if not offsetN.isnumeric():
            raise IndexError

        offsetN = int(offsetN)
        if sys.argv[2] == "month":
            returnVal = __monthsSinceEpoch(epochTime) % offsetN
        elif sys.argv[2] == "week":
            returnVal = int(epochTime/60/60/24/7) % offsetN
        elif sys.argv[2] == "day":
            returnVal = int(epochTime/60/60/24) % offsetN
        else:
            print(f"'{sys.argv[2]}' must be 'day', 'week', or 'month'.")
            return

        print(returnVal)

        if offsetN == 1:
            print(
                f"Note: Anything % 1 is always 0. This is saying 'every single {sys.argv[2]}'.\nOffsets are used to make sure a task will run for a given {sys.argv[2]}. '%1' means it will always run, so no need for an offset.\nPlease see the README for details, or just run 'remindmail help offset'.")
        elif returnVal == 0:
            print(
                "Note: The offset is 0, so a task for this date in remind.md will be added without an offset.")

    except ValueError:
        print(sys.argv[3])
        print("Date must be YYYY-MM-DD.")
    except IndexError:
        print(
            f"Missing <n>, as in 'every n {sys.argv[2]}s'\nUsage: remindmail offset {sys.argv[2]} {sys.argv[3]} nExample:\nFor help: 'remindmail help offset'")
        return


def parse():
    # parse reminder title
    query_time = ''
    query = ' '.join(sys.argv[1:])
    query = ''.join(re.split('me to ', query, flags=re.IGNORECASE)[
                    1:]) if re.search('me to ', query, re.IGNORECASE) else query
    query = ''.join(query.split('to ')[
        1:]) if query.startswith('to ') else query

    if query.__contains__(" at ") or query.__contains__(" on "):
        # look for weekdays using 'on {dayw}'
        for day in ['on sun',
                    'on mon',
                    'on tue',
                    'on wed',
                    'on thu',
                    'on fri',
                    'on sat',
                    'next sun',
                    'next mon',
                    'next tue',
                    'next wed',
                    'next thu',
                    'next fri',
                    'next sat',
                    'sunday',
                    'monday',
                    'tuesday',
                    'wednesday',
                    'thursday',
                    'friday',
                    'saturday']:

            if re.search(day, query, flags=re.IGNORECASE):

                _query_match = re.split(day, query, flags=re.IGNORECASE)
                query = _query_match[0] if len(
                    _query_match[0]) > len(_query_match[1]) else _query_match[1]

                query_time = day
                query_time = re.sub('on ', '', query_time, flags=re.IGNORECASE)
                query_time = re.sub('next ', '', query_time,
                                    flags=re.IGNORECASE)
                query_time = re.sub('day', '', query_time, flags=re.IGNORECASE)
                break

        if query.startswith(' to ') or query.startswith('to ') or query.startswith('day to '):
            query = ''.join(query.split('to')[1:])

        if query_time:
            response = input(
                f"""Sending "{query.strip()}" on {__getWeekday(query_time)}- OK? y/n\n""")
            if len(response) > 0 and not response.startswith('n'):
                print("Adding...")
                query = query.strip()
                remindMd = securedata.getFileAsArray('remind.md', 'notes')
                remindMd.append(f"[{query_time}]d {query}")
                securedata.writeFile("remind.md", "notes", '\n'.join(remindMd))
                log(f"""Scheduled "{query}" for {__getWeekday(query_time)}""")
            return

        # TODO parse dates

    response = input(f"""Sending "{query}" right now- OK? y/n\n""")
    if len(response) > 0 and not response.startswith('n'):
        mail.send(f"Reminder - {query}", "Sent via Terminal")


params = {
    "help": help,
    "pull": pull,
    "config": config,
    "generate": generate,
    "offset": offset
}

if __name__ == '__main__':
    func = params.get(sys.argv[1], lambda: parse())
    func()
