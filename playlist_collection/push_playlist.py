#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Sync a playlist from one user to the other
	E.g. a playlist of user1 can be "send" to user2
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from re import findall as re_findall

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def push_playlist(ssn, source_user: str, target_users: list, playlist_name: str):
	result_json, source_token, target_tokens = [], '', []

	#check for illegal arg parsing
	if not target_users:
		return 'No target users selected'
	if source_user in target_users:
		return 'Source user also as target user selected'
	if source_user == '@all':
		return 'Source user can not be @all'

	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers', headers={}).text

	#add user self to target list if requested
	if ('@all' in target_users and source_user != '@me') or '@me' in target_users:
		target_tokens.append(plex_api_token)

	#set user self as source if requested
	if source_user == '@me':
		source_token = plex_api_token

	#get data about every user (username at beginning and token at end)
	user_data = re_findall(r'(?<=username=").*?accessToken="\w+?(?=")', shared_users)
	#loop through shared users; note source user and all target users
	for user in user_data:
		username = user.split('"')[0]
		if not source_token and username == source_user:
			source_token = user.split('"')[-1]
			continue
		if (not '@all' in target_users and not username in target_users) or username == source_user:
			continue
		token = user.split('"')[-1]
		target_tokens.append([username, token])

	if not source_token:
		return 'Source user not found'

	#get source playlist
	playlists = ssn.get(f'{base_url}/playlists', params={'X-Plex-Token': source_token}).json()['MediaContainer'].get('Metadata', [])
	for playlist in playlists:
		if playlist['title'] == playlist_name:
			#playlist found
			playlist_ratingkey = playlist['ratingKey']
			playlist_info = playlist
			break
	else:
		#playlist not found
		return 'Source playlist not found'

	playlist_content = ssn.get(f'{base_url}/playlists/{playlist_ratingkey}/items', params={'X-Plex-Token': source_token}).json()['MediaContainer'].get('Metadata', [])
	if not playlist_content: return 'Source playlist is empty'
	playlist_ratingkeys = [i['ratingKey'] for i in playlist_content]

	for target_token in target_tokens:
		print(target_token[0])
		#delete old playlist if it's there
		user_playlists = ssn.get(f'{base_url}/playlists', params={'X-Plex-Token': target_token[1]}).json()['MediaContainer'].get('Metadata',[])
		for user_playlist in user_playlists:
			if user_playlist['title'] == playlist_name:
				ssn.delete(f'{base_url}/playlists/{user_playlist["ratingKey"]}', params={'X-Plex-Token': target_token[1]})

		#create playlist for target user
		new_ratingkey = ssn.post(f'{base_url}/playlists', params={'X-Plex-Token': target_token[1], 'title': playlist_info['title'], 'smart': '0', 'type': playlist_info['playlistType'], 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(playlist_ratingkeys)}'}).json()['MediaContainer']['Metadata'][0]['ratingKey']
		if 'thumb' in playlist_info:
			#upload poster
			ssn.post(f'{base_url}/playlists/{new_ratingkey}/posters',  params={'X-Plex-Token': target_token[1], 'url': f'{base_url}{playlist_info["thumb"]}?X-Plex-Token={source_token}'})

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Sync a playlist from one user to the other')
	parser.add_argument('-s','--SourceUser', type=str, help='Username of the source user; @me to target yourself', required=True)
	parser.add_argument('-p','--PlaylistName', type=str, help='The name of the playlist to push', required=True)
	parser.add_argument('-t','--TargetUser', type=str, help='Username of the target user; @me to target yourself; @all to target everyone; give multiple times to target multiple users', action='append', required=True)

	args = parser.parse_args()
	#call function and process result
	response = push_playlist(ssn=ssn, source_user=args.SourceUser, target_users=args.TargetUser, playlist_name=args.PlaylistName)
	if not isinstance(response, list):
		parser.error(response)
