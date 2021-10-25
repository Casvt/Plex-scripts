#!/usr/bin/python3

#The use case of this script is the following:
#	When an episode is downloaded and imported in sonarr, unmonitor that episode
#SETUP:
#	Go to the sonarr web-ui -> Settings -> Connect -> + -> Custom Script
#		Name = whatever
#		Triggers = 'On Import' and 'On Upgrade'
#		Tags = whatever if needed
#		path = /path/to/unmonitor_downloaded_episodes.py
#IMPORTANT: Clicking the test button will return an error, however the script works fine. Ignore the error and complete setup.

sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''

import requests
import os
import re
from os import environ

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', sonarr_ip):
	print("Error: " + sonarr_ip + " is not a valid ip")
	exit(1)

if not re.search('^\d{1,5}$', sonarr_port):
	print("Error: " + sonarr_port + " is not a valid port")
	exit(1)

if not re.search('^[a-z0-9]{30,36}$', sonarr_api_token):
	print("Error: " + sonarr_api_token + " is not a valid api token")
	exit(1)

sonarr_episodefile_episodeids = str(environ.get('sonarr_episodefile_episodeids'))
requests.put('http://' + sonarr_ip + ':' + sonarr_port + '/api/v3/episode/monitor?apikey=' + sonarr_api_token, json={'episodeIds':[sonarr_episodefile_episodeids],'monitored':'false'})
