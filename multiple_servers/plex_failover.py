#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	When a local stream on the main server is buffering for x seconds, stop it and start it on the backup server
Requirements (python3 -m pip install [requirement]):
	requests
	PlexAPI
Setup:
	Fill the variables below firstly,
	then go to the tautulli web-ui -> Settings -> Notification Agents -> Add a new notification agent -> Script:
		Configuration:
			Script Folder = /path/to/script/folder
			Script File = select this script
			Script Timeout = 0
			Description = whatever you want
		Triggers:
			Playback Start = check
		Arguments:
			Playback Start -> Script Arguments = --SessionId {session_id}
"""

main_plex_ip = ''
main_plex_port = ''
main_plex_api_token = ''

backup_plex_ip = ''
backup_plex_port = ''
backup_plex_api_token = ''

from os import getenv
from time import sleep as time_sleep
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound as plexapi_notfound

# Environmental Variables
main_plex_ip = getenv('main_plex_ip', main_plex_ip)
main_plex_port = getenv('main_plex_port', main_plex_port)
main_plex_api_token = getenv('main_plex_api_token', main_plex_api_token)
main_base_url = f"http://{main_plex_ip}:{main_plex_port}"
backup_plex_ip = getenv('backup_plex_ip', backup_plex_ip)
backup_plex_port = getenv('backup_plex_port', backup_plex_port)
backup_plex_api_token = getenv('backup_plex_api_token', backup_plex_api_token)
backup_base_url = f"http://{backup_plex_ip}:{backup_plex_port}"

def plex_failover_switch(main_plex_ssn, backup_plex_ssn, media_id: str, player: str, offset: int=0):
	main_plex = PlexServer(main_base_url, main_plex_api_token)
	backup_plex = PlexServer(backup_base_url, backup_plex_api_token)

	#get info about source media
	media_info = main_plex_ssn.get(f'{main_base_url}/library/metadata/{media_id}', params={'includeGuids': '1'})
	if media_info.status_code != 404:
		lib_id = str(media_info.json()['MediaContainer']['librarySectionID'])
		sections = main_plex_ssn.get(f'{main_base_url}/library/sections').json()['MediaContainer']['Directory']
		for lib in sections:
			if lib['key'] == lib_id:
				lib_type = lib['type']
				break
		else:
			return 'Library type not found'

		media_info = media_info.json()['MediaContainer']['Metadata'][0]
		if 'Guid' in media_info:
			media_info = media_info['Guid']
		else:
			media_info = media_info['title']
	else:
		return 'Media not found'
	#summary: lib_type = source lib type, lib_id = source lib id, media_info = source title (str) or source guids (list)

	#try to find media on backup server
	target_key = ''
	sections = backup_plex_ssn.get(f'{backup_base_url}/library/sections').json()['MediaContainer']['Directory']
	for lib in sections:
		if lib['type'] != lib_type: continue
		if lib['type'] == 'show':
			lib_output = backup_plex_ssn.get(f'{backup_base_url}/library/sections/{lib["key"]}/all', params={'includeGuids': '1', 'type': '4'}).json()['MediaContainer']['Metadata']
		else:
			lib_output = backup_plex_ssn.get(f'{backup_base_url}/library/sections/{lib["key"]}/all', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']

		for media in lib_output:
			if isinstance(media_info, list) and 'Guid' in media and media['Guid'] == media_info:
				#media found on backup server using guids (reliable)
				target_key = f'/library/metadata/{media["ratingKey"]}'
				break

			elif isinstance(media_info, str) and 'title' in media and media['title'] == media_info:
				#media found on backup server using title (unreliable)
				target_key = f'/library/metadata/{media["ratingKey"]}'
				break
		else:
			continue
		break

	#stop stream and if media is found on backup server, start stream from backup server
	try:
		client = main_plex.client(player)
		client.stop(mtype='video')
	except plexapi_notfound:
		return 'Client on main plex server not found'

	if target_key:
		try:
			client = backup_plex.client(player)
			media = backup_plex.fetchItem(target_key)
			client.playMedia(media, offset=offset, key=target_key)
		except plexapi_notfound:
			return 'Client on backup plex server not found'
		return 'Success: send stream to backup server'
	else:
		return 'Success: stopped stream'

def plex_failover(main_plex_ssn, backup_plex_ssn, session_id: str, buffer_threshold: int=10, check_interval: int=5):
	while True:
		sessions = main_plex_ssn.get(f'{main_base_url}/status/sessions').json()['MediaContainer']
		if not 'Metadata' in sessions:
			#session not found or ended
			return 'Session ended'
		for session in sessions['Metadata']:
			if session['Session']['id'] == session_id:
				#session found
				if session['Session']['location'] != 'lan': return 'Session not local; ignoring'
				session_state = session['Player']['state']
				if session_state == 'buffering':
					#session is buffering; check if it's still in {buffer_threshold} seconds
					buffer_counter = 0
					for _ in range(buffer_threshold):
						#check if current state is buffering
						buffer_sessions = main_plex_ssn.get(f'{main_base_url}/status/sessions').json()['MediaContainer']
						if not 'Metadata' in buffer_sessions: return 'Session ended'
						for buffer_session in buffer_sessions['Metadata']:
							if buffer_session['Session']['id'] == session_id:
								if buffer_session['Player']['state'] == 'buffering':
									buffer_counter += 1
								break
						else: return 'Session ended'

						time_sleep(1)
					if buffer_counter == buffer_threshold:
						#session has been buffering for {buffer_threshold} seconds so initiate failover
						response = plex_failover_switch(main_plex_ssn, backup_plex_ssn, player=session['Player']['title'], media_id=session['ratingKey'], offset=session['viewOffset'])
						return f'Failover: {response}'
				break
		else:
			#session not found or ended
			return 'Session ended'

		time_sleep(check_interval)

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	main_plex_ssn = requests.Session()
	main_plex_ssn.headers.update({'Accept': 'application/json'})
	main_plex_ssn.params.update({'X-Plex-Token': main_plex_api_token})
	backup_plex_ssn = requests.Session()
	backup_plex_ssn.headers.update({'Accept': 'application/json'})
	backup_plex_ssn.params.update({'X-Plex-Token': backup_plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="When a local stream on the main server is buffering for x seconds, stop it and start it on the backup server")
	parser.add_argument('-s','--SessionId', type=str, help="The plex session id of the stream that should be monitored", required=True)
	parser.add_argument('-b','--BufferThreshold', type=int, help="The amount of seconds a stream should be buffering before the failover is triggered", default=10)
	parser.add_argument('-i','--CheckInterval', type=int, help="The interval in seconds that the script checks a stream", default=5)

	args = parser.parse_args()
	#call function and process result
	response = plex_failover(main_plex_ssn=main_plex_ssn, backup_plex_ssn=backup_plex_ssn, session_id=args.SessionId, buffer_threshold=args.BufferThreshold, check_interval=args.CheckInterval)
	print(response)
