#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	When a movie is downloaded and imported in radarr, unmonitor that movie
Setup:
	Fill the variables below firstly,
	then go to the radarr web-ui -> Settings -> Connect -> + -> Custom Script:
		Name = whatever you want
		Triggers = 'On Import' and 'On Upgrade'
		Tags = whatever if needed
		path = /path/to/unmonitor_downloaded_movies.py
"""

radarr_ip = ''
radarr_port = ''
radarr_api_token = ''

from os import getenv

# Environmental Variables
radarr_ip = getenv('radarr_ip', radarr_ip)
radarr_port = getenv('radarr_port', radarr_port)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)

def unmonitor_downloaded_movies(ssn, movie_id: str):
	result = ssn.put(f'http://{radarr_ip}:{radarr_port}/api/v3/movie/editor', json={'movieIds':[movie_id],'monitored': False})
	return result

#handle testing of the script by radarr
if getenv('radarr_eventtype') == 'Test':
	if radarr_ip and radarr_port and radarr_api_token:
		exit(0)
	else:
		print('Error: Not all variables are set')
		exit(1)

if __name__ == '__main__':
	import requests

	#setup vars
	ssn = requests.Session()
	ssn.params.update({'apikey': radarr_api_token})
	movie_id = str(getenv('radarr_movie_id'))

	#call function
	unmonitor_downloaded_movies(ssn, movie_id)
