#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Distribute local streams over two plex servers so that the load on both servers is even
Requirements (python3 -m pip install [requirement]):
	requests
	PlexAPI
Setup:
	Fill the variables below firstly,
	then ON BOTH SERVERS, go to their tautulli web-ui's -> Settings -> Notification Agents -> Add a new notification agent -> Script:
		Configuration:
			Script Folder = /path/to/script/folder
			Script File = select this script
			Script Timeout = 60
			Description = whatever you want
		Triggers:
			Playback Start = check
			Playback Stop = check
		Arguments:
			Playback Start -> Script Arguments = --SessionId {session_id}
Setup without Tautulli:
	Fill the variables below firstly, then run the script with -h to see the arguments that you can give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every 5m or every 1h).
"""

main_plex_ip = ''
main_plex_port = ''
main_plex_api_token = ''

backup_plex_ip = ''
backup_plex_port = ''
backup_plex_api_token = ''

from os import getenv
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

def plex_loadbalancer(main_plex_ssn, backup_plex_ssn, session_id: str=None, prefered_server: str='main'):
	result_json = {}
	main_plex = PlexServer(main_base_url, main_plex_api_token)
	backup_plex = PlexServer(backup_base_url, backup_plex_api_token)

	#keep moving streams until they're in balance over the servers
	while True:
		#get all the streams from both servers
		main_sessions = main_plex_ssn.get(f'{main_base_url}/status/sessions').json()['MediaContainer']
		if 'Metadata' in main_sessions: main_sessions = main_sessions['Metadata']
		else: main_sessions = []
		backup_sessions = backup_plex_ssn.get(f'{backup_base_url}/status/sessions').json()['MediaContainer']
		if 'Metadata' in backup_sessions: backup_sessions = backup_sessions['Metadata']
		else: backup_sessions = []

		#check if streams are balanced
		if len(main_sessions) == len(backup_sessions):
			#streams are balanced evenly (e.g. 2-2 or 0-0)
			break

		if (prefered_server == 'main' and len(main_sessions) - 1 == len(backup_sessions)) \
		or (prefered_server == 'backup' and len(main_sessions) + 1 == len(backup_sessions)):
			#stream are balanced unevenly (e.g. 3-2 or 2-3 depending on prefered_server)
			break

		#move stream from one server to the other
		if len(main_sessions) > len(backup_sessions):
			#move a stream from main server to backup server
			source_plex = main_plex
			source_plex_ssn = main_plex_ssn
			source_base_url = main_base_url
			target_plex = backup_plex
			target_plex_ssn = backup_plex_ssn
			target_base_url = backup_base_url
			source_sessions = main_sessions

		elif len(main_sessions) < len(backup_sessions):
			#move a stream from backup server to main server
			source_plex = backup_plex
			source_plex_ssn = backup_plex_ssn
			target_plex = main_plex
			target_plex_ssn = main_plex_ssn
			source_sessions = backup_sessions

		#select source stream; if all fail (remote or media not found) exit
		for check_id in True, False:
			for stream in source_sessions:
				if check_id == True and session_id != None and stream['Session']['id'] != session_id: continue
				#session can possibly be used; check if client of session is on both servers
				try:
					source_client = source_plex.client(stream['Player']['title'])
					target_client = target_plex.client(stream['Player']['title'])
				except plexapi_notfound:
					#session not able to be moved
					continue

				#session can be moved; check if media of session is on both servers
				#get info about source media
				media_info = source_plex_ssn.get(f'{source_base_url}/library/metadata/{stream["ratingKey"]}', params={'includeGuids': '1'})
				lib_id = media_info.json()['MediaContainer']['librarySectionID']
				sections = source_plex_ssn.get(f'{source_base_url}/library/sections').json()['MediaContainer']['Directory']
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

				#try to find media on backup server
				target_key = ''
				sections = target_plex_ssn.get(f'{target_base_url}/library/sections').json()['MediaContainer']['Directory']
				for lib in sections:
					if lib['type'] != lib_type: continue
					if lib['type'] == 'show':
						lib_output = target_plex_ssn.get(f'{target_base_url}/library/sections/{lib["key"]}/all', params={'includeGuids': '1', 'type': '4'}).json()['MediaContainer']['Metadata']
					else:
						lib_output = target_plex_ssn.get(f'{target_base_url}/library/sections/{lib["key"]}/all', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']

					for media in lib_output:
						if isinstance(media_info, list) and 'Guid' in media and media['Guid'] == media_info:
							#media found on target server using guids (reliable)
							target_key = f'/library/metadata/{media["ratingKey"]}'
							break

						elif isinstance(media_info, str) and 'title' in media and media['title'] == media_info:
							#media found on target server using title (unreliable)
							target_key = f'/library/metadata/{media["ratingKey"]}'
							break
					else:
						continue
					break
				if not target_key:
					#media not found on target server
					continue

				#move session to target server
				source_client.stop(mtype='video')
				media = target_plex.fetchItem(target_key)
				target_client.playMedia(media, offset=stream['viewOffset'], key=target_key)
				print('Moved a session from one server to the other')
				break
			else:
				continue
			break

	result_json['main'] = main_sessions
	result_json['backup'] = backup_sessions

	return result_json

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
	parser = argparse.ArgumentParser(description="Distribute local streams over two plex servers so that the load on both servers is even")
	parser.add_argument('-s','--SessionId', type=str, help="The plex session id of the stream that will be prefered to be moved if needed; only needed for Tautulli setup")
	parser.add_argument('-p','--PreferedServer', choices=['main','backup'], help="To which server should the restant stream go if there are uneven amount of streams", default='main')

	args = parser.parse_args()
	#call function and process result
	response = plex_loadbalancer(main_plex_ssn=main_plex_ssn, backup_plex_ssn=backup_plex_ssn, session_id=args.SessionId, prefered_server=args.PreferedServer)
	print(response)
