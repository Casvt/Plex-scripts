#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	When an episode is downloaded and imported in sonarr, unmonitor that episode
Setup:
	Fill the variables below firstly,
	then go to the sonarr web-ui -> Settings -> Connect -> + -> Custom Script:
		Name = whatever you want
		Triggers = 'On Download' and 'On Upgrade'
		Tags = whatever if needed
		path = /path/to/unmonitor_downloaded_episodes.py
"""

sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''

from os import getenv

# Environmental Variables
sonarr_ip = getenv('sonarr_ip', sonarr_ip)
sonarr_port = getenv('sonarr_port', sonarr_port)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)

def unmonitor_downloaded_episodes(ssn, episode_id: str):
	result = ssn.put(f'http://{sonarr_ip}:{sonarr_port}/api/v3/episode/monitor', json={'episodeIds':[episode_id],'monitored': False})
	return result

#handle testing of the script by sonarr
if getenv('sonarr_eventtype') == 'Test':
	if sonarr_ip and sonarr_port and sonarr_api_token:
		exit(0)
	else:
		print('Error: Not all variables are set')
		exit(1)

if __name__ == '__main__':
	import requests

	#setup vars
	ssn = requests.Session()
	ssn.params.update({'apikey': sonarr_api_token})
	episode_id = str(getenv('sonarr_episodefile_episodeids'))

	#call function
	unmonitor_downloaded_episodes(ssn, episode_id)
