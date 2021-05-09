# ReadMe
# A tool for editing Tasks.txt in Dropbox; to be integrated with Raspberry Pilot

import os
import sys
import subprocess
import json
from datetime import datetime as date
import time

sys.path.insert(0, '/home/pi/Git/google-reminders-cli')
sys.path.insert(0, '/home/pi/Git/SecureData')
import secureData
from remind import tasks

helpText = f"""\nUsage: tasks <command>\n\n<command>:
	add <taskInfo>
	add <taskInfo> <line number>
	rm  <taskInfo>
	rm  <line number>
	ls
	pull
	config notespath <notesPath>
	config cloud
	config cloudpath
	
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

# generates tasks from the TasksGenerate.txt file in {notesPath}. Not intended to be run directly (try 'crontab -e')
def generate():
	dayOfMonthTasksGenerated = secureData.variable("tasksGenerated")
	dayOfMonthTasksGenerated = dayOfMonthTasksGenerated if dayOfMonthTasksGenerated != '' else 0

	if(str(date.today().day) != dayOfMonthTasksGenerated):
		secureData.log("Generating tasks")

		epochDay = int(time.time()/60/60/24)
		epochWeek = int(time.time()/60/60/24/7)
		epochMonth = int(date.today().month)

		dayOfMonthEnclosed = "[D{:02d}]".format(today.day)
		dayOfWeekEnclosed = f"[{today.strftime('%a').lower()}]"
		dateMMdashDDEnclosed = f"[{today.strftime('%m-%d')}]"
		for item in secureData.array("TasksGenerate.txt", "notes"):
			if(item.startswith(dayOfMonthEnclosed) or item.startswith(dayOfWeekEnclosed) or item.startswith(dateMMdashDDEnclosed)):
				secureData.appendUnique("Tasks.txt", item, "notes")
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
						secureData.appendUnique("Tasks.txt", item, "notes")
				elif(splitType == "w"):
					if(date.today().strftime("%a") == 'Sun' and epochWeek % splitFactor == splitOffset):
						secureData.appendUnique("Tasks.txt", item, "notes")
				elif(splitType == "m"):
					if(date.today().day == 1 and epochMonth % splitFactor == splitOffset):
						secureData.appendUnique("Tasks.txt", item, "notes")

		secureData.write("tasksGenerated", str(date.today().day))
		secureData.log("Generated tasks")
	else:
		print(f"Tasks have already been generated in the past 12 hours (most recently on Day {dayOfMonthTasksGenerated} of this month).")


def add(s=None):
	if(s == "help"):
		return "Add something"
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
	
def rm(s=None):
	if(s == "help"):
		return f"Pulls latest Tasks.txt in secureData.piTasksNotesPath (currently {secureData.piTasksNotesPath}), then removes the selected string or index in the file.\n\ne.g. 'tasks rm 3' removes the third line.\n\nUsage: tasks rm '<string matching task title, or integer of a line to remove>'"
	if(len(sys.argv) < 3):
		print(rm("help"))
		return

	# convert list and query to lowercase to avoid false negatives
	tasks = __toLower(secureData.array("Tasks.txt", "notes"))
	
	args = sys.argv[2:]
	args.sort(reverse=True)

	for arg in args:
		arg = arg.lower()

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
		
	
params = {
	"add": add,
	"rm": rm,
	"rename": rename,
	"ls": ls,
	"help": help,
	"pull": pull,
	"config": config,
	"generate": generate
}

if(len(sys.argv)) == 1:
	print(helpText)
	quit()
	
if __name__ == '__main__':
	func = params.get(sys.argv[1], lambda: print(helpText))
	func()
