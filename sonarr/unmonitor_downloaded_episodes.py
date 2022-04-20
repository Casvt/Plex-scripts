#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	When an episode is downloaded and imported in sonarr, unmonitor that episode
SETUP:
	Go to the sonarr web-ui -> Settings -> Connect -> + -> Custom Script
		Name = whatever you want
		Triggers = 'On Download' and 'On Upgrade'
		Tags = whatever if needed
		path = /path/to/unmonitor_downloaded_episodes.py
"""

sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''

import requests
from os import environ

if environ.get('sonarr_eventtype') == 'Test':
	if sonarr_ip and sonarr_port and sonarr_api_token:
		exit(0)
	else:
		print('Error: Not all variables are set')
		exit(1)

sonarr_episodefile_episodeids = str(environ.get('sonarr_episodefile_episodeids'))
requests.put('http://' + sonarr_ip + ':' + sonarr_port + '/api/v3/episode/monitor?apikey=' + sonarr_api_token, json={'episodeIds':[sonarr_episodefile_episodeids],'monitored': False})
