import random

#The use case of this script is the following:
#   When you're watching Avengers: Infinity War, at the moment that thanos snaps, this script will be launched.
#   When the script is launched, there is a 50/50 chance that a command to your liking is executed
#
#SETUP:
#In Tautulli, go to Settings -> Notification Agents -> Add a new notification agent -> Script
#	Configuration:
#		Script Folder = folder where this script is stored
#		Script File = select this script
#		Script Timeout = 0
#		Description is optional
#	Triggers:
#		Playback Start = check
#   Conditions:
#       Condition {1} = Progress Duration (sec) is 7866
#       Condition {2} = Title is Avengers: Infinity War
#       Condition Logic = {1} and {2}
#SAVE
#
#WARNING: THERE'S A 50/50 CHANCE THAT A COMMAND IS EXECUTED THAT COULD LEAD TO DESTRUCTION OF FILES/DIRECTORIES
#         I AM NOT RESPONSIBLE FOR ANY LOSS OF IMPORTANT DATA

if random.randrange(1,3) == 2:
	print('It\'s not your lucky day')
	#place destructive command here
else:
	print('It\s your lucky day')
