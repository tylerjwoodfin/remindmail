# ReadMe
# A tool for editing Tasks.txt in Dropbox; to be integrated with Raspberry Pilot

import os
import sys
import subprocess
import json
import tempfile
from datetime import datetime as date
from subprocess import call
import time

sys.path.insert(0, '/home/pi/Git/google-reminders-cli')
sys.path.insert(0, '/home/pi/Git/SecureData')
import secureData
from remind import tasks

helpText = f"""\nUsage: tasks <command>\n\n<command>:
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
	
	For help with a specific command: tasks help <command>
	
Parameters:
	taskInfo: enter any task you want to complete. Enclose in quotes, e.g. tasks add 'take the trash out'
	notesPath: Currently {secureData.piTasksNotesPath}. Setting is stored at {secureData.securePath}/PiTasksNotesPath.

Notes Directory:
	Tasks.txt and TasksGenerate.txt in {secureData.piTasksNotesPath}. Change the path by running "tasks config notes <fullPath>" (stored in {secureData.securePath}/PiTasksNotesPath)

TasksGenerate.txt:
	when generate() is run (from crontab or similar task scheduler; not intended to be run directly), matching tasks are added to Tasks.txt.
	See the provided example TasksGenerate.md in ReadMe.
	
	"""


today = date.today()

def __toLower(arr):
	for i in range(len(arr)):
		arr[i] = arr[i].lower()
	
	return arr

def __monthsSinceEpoch(epoch):
	epochTime = time.localtime(epoch)
	return ((epochTime.tm_year - 1970) * 12) + epochTime.tm_mon

# generates tasks from the TasksGenerate.txt file in {notesPath}. Not intended to be run directly (try 'crontab -e')
def generate():
	dayOfMonthTasksGenerated = secureData.variable("tasksGenerated")
	dayOfMonthTasksGenerated = dayOfMonthTasksGenerated if dayOfMonthTasksGenerated != '' else 0

	if(str(date.today().day) != dayOfMonthTasksGenerated and date.today().hour > 0):
		secureData.log("Generating tasks")

		epochDay = int(time.time()/60/60/24)
		epochWeek = int(time.time()/60/60/24/7)
		epochMonth = int(date.today().month)

		dayOfMonthEnclosed = "[d{:02d}]".format(today.day)
		dayOfWeekEnclosed = f"[{today.strftime('%a').lower()}]"
		dateMMdashDDEnclosed = f"[{today.strftime('%m-%d')}]"

		# read files
		tasksFile = secureData.array("Tasks.txt", "notes")
		tasksGenerateFile = secureData.array("TasksGenerate.txt", "notes")

		for item in tasksGenerateFile:
			if(item.startswith(dayOfMonthEnclosed.lower()) or item.startswith(dayOfWeekEnclosed) or item.startswith(dateMMdashDDEnclosed)):
				tasksFile.append(item)
			elif(item.startswith("[") and ("%" in item) and ("]" in item)):
				splitType = item[1].lower() # d, w, m
				splitFactor = item.split("%")[1].split("]")[0]
				splitOffset = 0

				# e.g. [D%4+1] for every 4 days, offset 1
				if("+" in splitFactor):
					splitOffset = int(splitFactor.split("+")[1])
					splitFactor = int(splitFactor.split("+")[0])
				else:
					splitFactor = int(splitFactor)

				if(splitType == "d"):
					if(epochDay % splitFactor == splitOffset):
						tasksFile.append(item)
				elif(splitType == "w"):
					if(date.today().strftime("%a") == 'Sun' and epochWeek % splitFactor == splitOffset):
						tasksFile.append(item)
				elif(splitType == "m"):
					if(date.today().day == 1 and epochMonth % splitFactor == splitOffset):
						tasksFile.append(item)
				elif(splitType in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']):
					if(date.today().strftime("%a") == splitType and epochWeek % splitFactor == splitOffset):
						tasksFile.append(item)

			# handle deletion
			if("]d" in item):
				tasksGenerateFile.remove(item)

		# filter to unique items
		tasksFile = list(dict.fromkeys(tasksFile))
		
		secureData.write("Tasks.txt", '\n'.join(tasksFile), "notes")
		secureData.write("TasksGenerate.txt", '\n'.join(tasksGenerateFile), "notes")
		secureData.write("tasksGenerated", str(date.today().day))
		secureData.log("Generated tasks")
	else:
		print(f"Tasks have already been generated in the past 12 hours.")


def add(s=None):
	if(s == "help"):
		return "Pulls latest Tasks.txt in secureData.piTasksNotesPath (currently {secureData.piTasksNotesPath}), then adds the string to the file.\n\ne.g. 'tasks add \"buy milk\"'"
	if(len(sys.argv) < 3):
		print(rm("help"))
		return

	dayOfWeekEnclosed = f"[{today.strftime('%a').lower()}]"

	tasks = secureData.array("Tasks.txt", "notes")

	for arg in sys.argv[2:]:
		tasks.append(f"{dayOfWeekEnclosed} {arg}")
		print(f"Added {arg} to {secureData.piTasksNotesPath}Tasks.txt")
	
	secureData.write("Tasks.txt", '\n'.join(tasks), "notes")
	ls()

def edit(s=None):
	if(s == "help"):
		return ""

	EDITOR = os.environ.get('EDITOR','vim')

	tasks = secureData.file("Tasks.txt", "notes") # if you want to set up the file somehow

	with tempfile.NamedTemporaryFile(mode='w+', suffix=".tmp") as tf:
		tf.write(tasks)
		tf.flush()
		call([EDITOR, tf.name])
		tf.seek(0)
		new_tasks = tf.read()

		if(tasks != new_tasks):
			print("Saving...")
			secureData.write("Tasks.txt", new_tasks, "notes")
			print(f"Saved to {secureData.piTasksNotesPath}Tasks.txt.")
		else:
			print("No changes made.")
	
def rm(s=None):
	if(s == "help"):
		return f"Pulls latest Tasks.txt in secureData.piTasksNotesPath (currently {secureData.piTasksNotesPath}), then removes the selected string or index from the file.\n\ne.g. 'tasks rm 3' removes the third line.\n\nUsage: tasks rm '<string matching task title, or integer of a line to remove>'"
	if(len(sys.argv) < 3):
		print(rm("help"))
		return

	# convert list and query to lowercase to avoid false negatives
	tasks = __toLower(secureData.array("Tasks.txt", "notes"))
	
	args = sys.argv[2:]
	
	# convert numeric parameters to integers for proper sorting
	for i, arg in enumerate(args):
		if(arg.isnumeric()):
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
				if(arg == task or (task.startswith("[") and "] " in task and arg == task.split("] ")[1])):
					del tasks[i]
					secureData.write("Tasks.txt", '\n'.join(tasks), "notes")
					print(f"Removed {arg}.")
					secureData.log("Removed a Task. Good job!")
					continue

				print(f"'{arg}' isn't in {secureData.piTasksNotesPath}Tasks.txt.\nHint: don't include brackets. Names must be an exact, case-insensitive match.")

	secureData.write("Tasks.txt", '\n'.join(tasks), "notes")
	ls()

def rename(s=None):
	if(s == "help"):
		return f"Pulls latest Tasks.txt in secureData.piTasksNotesPath (currently {secureData.piTasksNotesPath}), then renames the selected string or index in the file.\n\ne.g. 'tasks rename 3 'buy milk' renames the third line to 'buy milk'.\ne.g. 'tasks rename 'buy milk' 'buy water' renames all lines called 'buy milk' to 'buy water'.\n\nUsage: tasks rename <string matching task title, or integer of a line to remove> <replacement string>"
	if(len(sys.argv) < 4):
		print(rm("help"))
		return

	# convert list and query to lowercase to avoid false negatives
	tasks = __toLower(secureData.array("Tasks.txt", "notes"))
	sys.argv[2] = sys.argv[2].lower()
	dayOfWeekEnclosed = f"[{today.strftime('%a').lower()}]"

	try:
		tasks[int(sys.argv[2])-1] = f"{dayOfWeekEnclosed} {sys.argv[3]}"
		secureData.write("Tasks.txt", '\n'.join(tasks), "notes")
		print(f"Renamed {sys.argv[2]} to {sys.argv[3]}. New Tasks:\n")
		ls()
	except:
		for i, task in enumerate(tasks):
			if(sys.argv[2] == task or (task.startswith("[") and "] " in task and sys.argv[2] == task.split("] ")[1])):
				tasks[i] = f"{dayOfWeekEnclosed} {sys.argv[3]}"
				secureData.write("Tasks.txt", '\n'.join(tasks), "notes")
				print(f"Renamed {sys.argv[2]} to {sys.argv[3]}. New Tasks:\n")
				ls()
				quit()
				
		print(f"'{sys.argv[2]}' isn't in {secureData.piTasksNotesPath}Tasks.txt.\nHint: don't include brackets. Names must be an exact, case-insensitive match.")

def ls(s=None):
	if(s == "help"):
		return f"Displays the latest Tasks.txt in secureData.piTasksNotesPath (currently {secureData.piTasksNotesPath}), formatted with line numbers\n\nUsage: tasks ls"
	
	print("\n")
	os.system(f"rclone copyto {secureData.piTasksCloudProvider}{secureData.piTasksCloudProviderPath}/Tasks.txt {secureData.piTasksNotesPath}Tasks.txt; cat -n {secureData.piTasksNotesPath}Tasks.txt")
	print("\n")
	
def help():
	if(len(sys.argv) > 2):
		func = params.get(sys.argv[2])
		if(hasattr(func, '__name__')):
			print(func("help"))
	else:
		print(helpText)

def pull(s=None):
	if(s == "help"):
		return f"Pull reminders from Google Calendar, delete them, and add them to Tasks.txt in secureData.piTasksNotesPath (currently {secureData.piTasksNotesPath})"
		
	print("Pulling from Google...")
	items = tasks()

	# for each reminder, write to Tasks.txt if not there already
	titlesToAdd = []
	for item in items:
		print(item)
		if(not item["done"]):
			titlesToAdd.append(item['title'])
			print(f"Moving {item['title']} to {secureData.piTasksNotesPath}Tasks.txt")
		print(f"Deleting {item['title']}")
		print(subprocess.check_output(['/home/pi/Git/google-reminders-cli/remind.py', '-d', item['id']]))

	if(len(titlesToAdd) > 0):
		secureData.appendUnique("Tasks.txt", '\n'.join(titlesToAdd), "notes")

def config(s=None):
	if(s == "help"):
		return f"""tasks config notespath <path>: Set your notes path (use full paths)
		e.g. tasks config notes /home/pi/Dropbox/Notes
		(this is stored in your secureData folder as PiTasksNotesPath)
		
		tasks config cloud: Set your cloud storage provider based on your rclone config (must have rclone- see ReadMe)
		e.g. tasks config cloud
		(this is stored in your secureData folder as PiTasksCloudProvider)
		
		tasks config cloudpath <path>: Set the path in your cloud service to store Tasks.txt
		e.g., if you keep Tasks in Dropbox at Documents/Notes/Tasks.txt: tasks config cloudpath Documents/Notes
		(this is stored in your secureData folder as PiTasksCloudProviderPath)"""
	if(len(sys.argv) < 3):
		print(config("help"))
		return

	if(sys.argv[2].lower() == "notespath"):
		newDir = sys.argv[3] if sys.argv[3][-1] == '/' else sys.argv[3] + '/'
		secureData.write("PiTasksNotesPath", newDir)
		print(f"Tasks.txt and TasksGenerate.txt should now be stored in {newDir}.")

	if(sys.argv[2].lower() == "cloud"):
		newDir = sys.argv[3] if sys.argv[3][-1] == '/' else sys.argv[3] + '/'
		secureData.write("PiTasksCloudProvider", newDir)
		print(f"Tasks.txt and TasksGenerate.txt should now be stored in {newDir}.")

def offset(s=None):
	if(s == "help"):
		return f"""Calculates the offset for a certain date (today by default)

		tasks offset <type> <date (YYYY-MM-DD, optional)> <n>
		(type is day, week, month)
		(n is 'every n days')

		Take the results of this function and use it to add an offset to a function.
		If you want something to happen every 3 days starting tomorrow, use:
		tasks offset day <tomorrow's date YYYY-MM-DD> 3

		If the answer is 2, then you can add this to TasksGenerate.txt:
		[D%3+2] Task here
		
		e.g. tasks offset day 2022-12-31 12
		(find offset for every 12 days intersecting 2022-12-31)

		e.g. tasks offset week 2022-12-31 3
		(every 3 weeks intersecting 2022-12-31)

		e.g. tasks offset month 2022-12-31 4
		(every 4 months intersecting 2022-12-31)

		e.g. tasks offset day 2022-12-31 5
		e.g. tasks offset week 2022-12-31 6
		e.g. tasks offset month 2022-12-31 7"""

	if(len(sys.argv) < 4):
		print("Usage: tasks offset <type (day,week,month)> <date (optional, YYYY-MM-DD)> <n, as in 'every n <type>'>\nExample: tasks offset week 2021-05-20 2\nFor help: 'tasks help offset'")
		return

	if(len(sys.argv) > 4):
		epochTime = int(date.strptime(sys.argv[3], "%Y-%m-%d").timestamp())
		offsetN = sys.argv[4]
	else:
		offsetN = sys.argv[-1]
		epochTime = int(time.time())
	
	try:
		if(not offsetN.isnumeric()):
			raise IndexError

		offsetN = int(offsetN)
		if(sys.argv[2] == "month"):
			returnVal = __monthsSinceEpoch(epochTime) % offsetN
		elif(sys.argv[2] == "week"):
			returnVal = int(epochTime/60/60/24/7) % offsetN
		elif(sys.argv[2] == "day"):
			returnVal = int(epochTime/60/60/24) % offsetN
		else:
			print(f"'{sys.argv[2]}' must be 'day', 'week', or 'month'.")
			return

		print(returnVal)

		if(offsetN == 1):
			print(f"Note: Anything % 1 is always 0. This is saying 'every single {sys.argv[2]}'.\nOffsets are used to make sure a task will run for a given {sys.argv[2]}. '%1' means it will always run, so no need for an offset.\nPlease see the README for details, or just run 'tasks help offset'.")
		elif(returnVal == 0):
			print("Note: The offset is 0, so a task for this date in TasksGenerate.md will be added without an offset.")

	except ValueError:
		print(sys.argv[3])
		print("Date must be YYYY-MM-DD.")
	except IndexError:
		print(f"Missing <n>, as in 'every n {sys.argv[2]}s'\nUsage: tasks offset {sys.argv[2]} {sys.argv[3]} nExample:\nFor help: 'tasks help offset'")
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

if(len(sys.argv)) == 1:
	print(f"Opening {secureData.piTasksNotesPath}Tasks.txt. Run 'tasks help' for help...")
	edit()
	quit()
	
if __name__ == '__main__':
	func = params.get(sys.argv[1], lambda: print(helpText))
	func()
