#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Stop all local plex streams when turned on and start them back up where the left off when turned off
Requirements (python3 -m pip install [requirement]):
	requests
	PlexAPI
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import os
from json import dump, load
from plexapi.exceptions import NotFound as plexapi_notfound

# Environmental Variables
plex_ip = os.getenv('plex_ip', plex_ip)
plex_port = os.getenv('plex_port', plex_port)
plex_api_token = os.getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def plex_maintenance_switch(ssn, plex, set_state: str='on'):
	result_json = []

	#check for illegal arg parsing
	if not set_state in ['on','off']:
		return 'Invalid value for set_state, "on" and "off" are allowed'

	if set_state == 'on':
		#note all streams down and stop them
		sessions = ssn.get(f'{base_url}/status/sessions').json()['MediaContainer']
		if 'Metadata' in sessions:
			#loop through all sessions
			for session in sessions['Metadata']:
				if session['Session']['location'] != 'lan': continue

				#note down info
				session_info = {
					"player": session['Player']['title'],
					"media": session['key'],
					"offset": session['viewOffset']
				}
				result_json.append(session_info)

				#stop stream
				try:
					plex.client(session['Player']['title']).stop(mtype='video')
				except plexapi_notfound:
					continue

			#note down all sessions in a file if any
			if result_json:
				file_name = os.path.splitext(__file__)[0] + '.json'
				with open(file_name, 'w') as f:
					dump(result_json, f, indent=4)

	elif set_state == 'off':
		#get all streams that were noted down
		file_name = os.path.splitext(__file__)[0] + '.json'
		if os.path.isfile(file_name):
			with open(file_name, 'r') as f:
				file_json = load(f)

			#go through all noted sessions
			for session in file_json:
				try:
					media = plex.fetchItem(session['media'])
					plex.client(session['player']).playMedia(media, key=session['media'], offset=session['offset'])
					result_json.append(session)
				except plexapi_notfound:
					continue
			
			#remove old file
			os.remove(file_name)

	return result_json

if __name__ == '__main__':
	import requests, argparse
	from plexapi.server import PlexServer

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})
	plex = PlexServer(base_url, plex_api_token)

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Stop all local plex streams when turned on and start them back up where the left off when turned off")
	parser.add_argument('-n', '--On', help="Turn maintenance mode on", action='store_true')
	parser.add_argument('-f', '--Off', help="Turn maintenance mode off", action='store_true')

	args = parser.parse_args()
	if args.On == True and args.Off == True:
		parser.error('Both -n/--On and -f/--Off are given which is not allowed')
	#call function and process result
	response = plex_maintenance_switch(ssn=ssn, plex=plex, set_state='on' if args.On == True else 'off')
	if not isinstance(response, list):
		parser.error(response)
