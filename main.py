from logging import exception
import client
import os
import sys
import tempfile
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
	add <taskInfo>
	add <taskInfo> <line number>
	edit
	rm  <taskInfo>
	rm  <line number>
	ls
	pull
	config notespath <notesPath>
	config cloud
	config cloudpath
	offset
	
	For help with a specific command: remindmail help <command>
	
Parameters:
	taskInfo: enter any task you want to complete. Enclose in quotes, e.g. remindmail add 'take the trash out'
	notesPath: Currently {path_local}. Settings are stored in {securedata.getConfigItem('path_securedata')} and should be stored as a JSON object (path -> remindmail -> local).

Notes Directory:
	Tasks.md and remind.md in {path_local}. Change the path by running "remindmail config notes <fullPath>" (stored in {securedata.getConfigItem('path_securedata')})

remind.md:
	when generate() is run (from crontab or similar task scheduler; not intended to be run directly), matching tasks are added to Tasks.md.
	See the provided example remind.md in ReadMe.
	
	"""


def __toLower(arr):
    return list(map(lambda x: x.lower(), arr))


def __monthsSinceEpoch(epoch):
    epochTime = time.localtime(epoch)
    return ((epochTime.tm_year - 1970) * 12) + epochTime.tm_mon


"""
Generates tasks from the remind.md file in {notesPath}.
Intended to be run from crontab (try 'remindmail generate force' to run immediately)
"""


def generate():
    dayOfMonthTasksGenerated = str(
        securedata.getItem("tasks", "day_generated"))

    dayOfMonthTasksGenerated = dayOfMonthTasksGenerated if dayOfMonthTasksGenerated != '' else 0

    if (str(datetime.today().day) != dayOfMonthTasksGenerated and datetime.today().hour > 0) or (len(sys.argv) > 2 and sys.argv[2] == "force"):
        securedata.log("Generating tasks")

        epochDay = int(time.time()/60/60/24)
        epochWeek = int(time.time()/60/60/24/7)
        epochMonth = int(datetime.today().month)

        dayOfMonthEnclosed = "[d{:02d}]".format(today.day)
        dayOfWeekEnclosed = f"[{today.strftime('%a').lower()}]"
        dateMMdashDDEnclosed = f"[{today.strftime('%m-%d')}]"

        try:
            tasksGenerateFile = securedata.getFileAsArray(
                "remind.md", "notes")
        except exception as e:
            securedata.log(
                "Could not read remind.md; Aborting", level="error")
            sys.exit("Could not read remind.md; Aborting")

        for item in tasksGenerateFile:
            if item.startswith(dayOfMonthEnclosed.lower()) or item.startswith(dayOfWeekEnclosed) or item.startswith(dateMMdashDDEnclosed):
                mail.send(f"Reminder - {item.split(' ', 1)[1]}", "")

                # handle deletion
                if "]d" in item:
                    securedata.log(f"Deleting item from TasksGenerate: {item}")
                    tasksGenerateFile.remove(item)

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
                    securedata.log(
                        f"Could not send reminder from TasksGenerate: {e}", level="error")

                # handle deletion
                if "]d" in item:
                    securedata.log(f"Deleting item from TasksGenerate: {item}")
                    tasksGenerateFile.remove(item)

        try:
            securedata.writeFile("remind.md", "notes",
                                 '\n'.join(tasksGenerateFile))
            securedata.setItem("tasks", "day_generated", datetime.today().day)
        except exception as e:
            securedata.log("Could not rewrite remind.md", level="error")
        securedata.log("Generated tasks")
    else:
        print(f"Tasks have already been generated in the past 12 hours.")


"""
Adds a task to the Tasks file

Parameter:
- s: string; the task name. Passing 'help' will only return the help information for this function.
"""


def add(s=None):
    if s == "help":
        return f"Pulls latest Tasks.md in path_local (currently {path_local}), then adds the string to the file.\n\ne.g. 'remindmail add \"buy milk\"'"
    if len(sys.argv) < 3:
        print(rm("help"))
        return

    dayOfWeekEnclosed = f"[{today.strftime('%a').lower()}]"

    tasks = securedata.getFileAsArray("Tasks.md", "notes")

    for arg in sys.argv[2:]:
        tasks.append(f"{dayOfWeekEnclosed} {arg}")
        print(
            f"Added {arg} to {path_local}/Tasks.md")

    securedata.writeFile("Tasks.md", "notes", '\n'.join(tasks))

    ls()


"""
Opens the tasks file in Vim, then saves it. Depending on `securedata` settings, it may also sync to the cloud.

Parameter:
- s: string; currently unused. Passing 'help' will only return the help information for this function.
"""


def edit(s=None):
    if s == "help":
        return ""

    EDITOR = os.environ.get('EDITOR', 'vim')

    # if you want to set up the file somehow
    tasks = '\n'.join(securedata.getFileAsArray("Tasks.md", "notes"))

    with tempfile.NamedTemporaryFile(mode='w+', suffix=".tmp") as tf:
        tf.write(tasks)
        tf.flush()
        call([EDITOR, tf.name])
        tf.seek(0)
        new_tasks = tf.read()

        if tasks != new_tasks:
            print("Saving...")
            securedata.writeFile("Tasks.md", "notes", new_tasks)
            print(
                f"Saved to {path_local}/Tasks.md.")
        else:
            print("No changes made.")


"""
Removes a selected string or index from the tasks file.

Parameters:
- s: string; currently unused. Passing 'help' will only return the help information for this function.
"""


def rm(s=None):
    if s == "help":
        return f"Pulls latest Tasks.md in path_local (currently {path_local}), then removes the selected string or index from the file.\n\ne.g. 'remindmail rm 3' removes the third line.\n\nUsage: remindmail rm '<string matching task title, or integer of a line to remove>'"
    if len(sys.argv) < 3:
        print(rm("help"))
        return

    # convert list and query to lowercase to avoid false negatives
    tasks = __toLower(securedata.getFileAsArray("Tasks.md", "notes"))

    args = sys.argv[2:]

    # convert numeric parameters to integers for proper sorting
    for i, arg in enumerate(args):
        if arg.isnumeric():
            args[i] = int(arg)
        else:
            args[i] = arg.lower()

    args.sort(reverse=True)

    for arg in args:
        try:
            del tasks[int(arg)-1]
            print(f"Removed {arg}.")
        except:
            for i, task in enumerate(tasks):
                if arg == task or (task.startswith("[") and "] " in task and arg == task.split("] ")[1]):
                    del tasks[i]
                    securedata.writeFile("Tasks.md", "notes", '\n'.join(tasks))
                    print(f"Removed {arg}.")
                    securedata.log("Removed a Task. Good job!")
                    continue

                print(
                    f"'{arg}' isn't in {path_local}/Tasks.md.\nHint: don't include brackets. Names must be an exact, case-insensitive match.")

    securedata.writeFile("Tasks.md", "notes", '\n'.join(tasks))
    ls()


"""
Pulls latest Tasks.md in path_local, then renames the selected string or index in the file

Parameters:
- s: string; currently unused. Passing 'help' will only return the help information for this function.
"""


def rename(s=None):
    if s == "help":
        return f"Pulls latest Tasks.md in path_local (currently {path_local}), then renames the selected string or index in the file.\n\ne.g. 'remindmail rename 3 'buy milk' renames the third line to 'buy milk'.\ne.g. 'remindmail rename 'buy milk' 'buy water' renames all lines called 'buy milk' to 'buy water'.\n\nUsage: remindmail rename <string matching task title, or integer of a line to remove> <replacement string>"
    if len(sys.argv) < 4:
        print(rm("help"))
        return

    # convert list and query to lowercase to avoid false negatives
    tasks = __toLower(securedata.getFileAsArray("Tasks.md", "notes"))
    sys.argv[2] = sys.argv[2].lower()
    dayOfWeekEnclosed = f"[{today.strftime('%a').lower()}]"

    try:
        tasks[int(sys.argv[2])-1] = f"{dayOfWeekEnclosed} {sys.argv[3]}"
        securedata.writeFile("Tasks.md", "notes", '\n'.join(tasks))
        print(f"Renamed {sys.argv[2]} to {sys.argv[3]}. New Tasks:\n")
        ls()
    except:
        for i, task in enumerate(tasks):
            if sys.argv[2] == task or (task.startswith("[") and "] " in task and sys.argv[2] == task.split("] ")[1]):
                tasks[i] = f"{dayOfWeekEnclosed} {sys.argv[3]}"
                securedata.writeFile("Tasks.md", "notes", '\n'.join(tasks))
                print(f"Renamed {sys.argv[2]} to {sys.argv[3]}. New Tasks:\n")
                ls()
                quit()

        print(
            f"'{sys.argv[2]}' isn't in {path_local}/Tasks.md.\nHint: don't include brackets. Names must be an exact, case-insensitive match.")


"""
Displays the latest Tasks.md in path_local, formatted with line numbers

Usage: remindmail ls

Parameters:
- s: string; currently unused. Passing 'help' will only return the help information for this function.
"""


def ls(s=None):
    if s == "help":
        return f"Displays the latest Tasks.md in path_local (currently {path_local}), formatted with line numbers\n\nUsage: remindmail ls"

    print("\n")
    os.system(
        f"rclone copyto {path_cloud}/Tasks.md {path_local}/Tasks.md; cat -n {path_local}/Tasks.md")
    print("\n")


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
Pulls reminders from Google Calendar, deletes them, and adds them to Tasks.md in path_local
"""


def pull(s=None):
    if s == "help":
        return f"Pulls reminders from Google Calendar, deletes them, and adds them to Tasks.md in path_local (currently {path_local})"

    print("Pulling from Google...")

    cli = client.RemindersClient()

    try:
        items = cli.list_reminders(5)
    except Exception as e:
        securedata.log(
            f"Could not pull reminders from Google: {e}", level="warn")
        sys.exit(-1)

    # pull TasksGenerate from cloud
    if cloud_enabled:
        os.system(
            f"rclone copy {path_cloud} {path_local}")

    # for each reminder, either add it to TasksGenerate if > 1 day from now, or send an email now, then delete it
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
                securedata.log(
                    f"Could not write to TasksGenerate: {e}", level="critical")
                sys.exit(-1)
        else:
            try:
                mail.send(f"Reminder - {item['title'].split(']d ')[1]}", "")
            except Exception as e:
                try:
                    mail.send(f"Reminder - {item['title']}", "")
                except Exception as e:
                    securedata.log(
                        f"Could not send reminder email: {e}", level="warn")

        # delete
        if cli.delete_reminder(reminder_id=item['id']):
            securedata.log(
                f"Pulled and deleted {item['title']} from Google Reminders")
        else:
            securedata.log(
                f"Could not delete {item['title']} from Google Reminders", level="warning")

    # sync possibly-modified TasksGenerate
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
        return f"""remindmail config notespath <path>: Set your notes path (use full paths)
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

    if sys.argv[2].lower() == "notespath":
        newDir = sys.argv[3] if sys.argv[3][-1] == '/' else sys.argv[3] + '/'
        securedata.setItem("path", "remindmail", "local", newDir)
        print(
            f"Tasks.md and remind.md should now be stored in {newDir}.")

    if sys.argv[2].lower() == "cloud":
        newDir = sys.argv[3] if sys.argv[3][-1] == '/' else sys.argv[3] + '/'
        securedata.setItem("path", "remindmail", "local", newDir)
        print(
            f"Tasks.md and remind.md should now be stored in {newDir}.")


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


params = {
    "add": add,
    "edit": edit,
    "rm": rm,
    "rename": rename,
    "ls": ls,
    "help": help,
    "pull": pull,
    "config": config,
    "generate": generate,
    "offset": offset
}

if len(sys.argv) == 1:
    print(
        f"Opening {path_local}/Tasks.md. Run 'remindmail help' for help...")
    edit()
    quit()

if __name__ == '__main__':
    func = params.get(sys.argv[1], lambda: print(helpText))
    func()
