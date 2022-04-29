#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	When a movie is downloaded and imported in radarr, unmonitor that movie
SETUP:
	Go to the radarr web-ui -> Settings -> Connect -> + -> Custom Script
		Name = whatever you want
		Triggers = 'On Import' and 'On Upgrade'
		Tags = whatever if needed
		path = /path/to/unmonitor_downloaded_movies.py
"""

radarr_ip = ''
radarr_port = ''
radarr_api_token = ''

import requests
from os import environ

if environ.get('radarr_eventtype') == 'Test':
	if radarr_ip and radarr_port and radarr_api_token:
		exit(0)
	else:
		print('Error: Not all variables are set')
		exit(1)

radarr_movie_id = str(environ.get('radarr_movie_id'))
requests.put(f'http://{radarr_ip}:{radarr_port}/api/v3/movie/editor?apikey={radarr_api_token}', json={'movieIds':[radarr_movie_id],'monitored': False})
