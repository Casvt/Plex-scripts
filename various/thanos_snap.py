#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	A 50/50 chance that a command will be execute exactly when Thanos snaps it's fingers in Avangers: Infinity War
Requirements (python3 -m pip install [requirement]):
	NO REQUIREMENTS
Setup:
	Fill the variables below firstly, then go to the tautulli web-ui -> Settings -> Notification Agents -> Add a new notification agent -> Script:
		Configuration:
			Script Folder = /path/to/script/folder
			Script File = select this script
			Script Timeout = 0
			Description = whatever you want
		Triggers:
			Playback Start = check
		Conditions:
			Condition {1} = Progress Duration (sec) is 7866
			Condition {2} = Title is Avengers: Infinity War
			Condition Logic = {1} and {2}
Warning:
	THERE'S A 50/50 CHANCE THAT WHEN THANOS SNAPS IT'S FINGERS,
	A COMMAND IS EXECUTED THAT COULD LEAD TO DESTRUCTION OF FILES/DIRECTORIES/ETC.
	I AM NOT RESPONSIBLE FOR ANY LOSS OF IMPORTANT DATA
"""

import random

def thanos_snap():
	if random.randrange(1,3) == 2:
		print('It\'s not your lucky day')
		#place destructive command here
	else:
		print('It\s your lucky day')

if __name__ == '__main__':
	#call function
	thanos_snap()
