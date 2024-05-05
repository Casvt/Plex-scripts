#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Convert a .m3u file to a plex playlist
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.

Use with relative file path M3U files:
	- The script assumes the .m3u file is placed at the root of the music folder.
	- open the terminal from the folder with your music (and where the .m3u file is placed)
	- run the script with the additional argument "--LibraryPath" including the path of the files within Plex to your music library.
	Example:
	linux: python3 ./m3u_to_playlist.py -l "Music" -f "chill.m3u" -u @all -p /media/Music/
	windows: python .\m3u_to_playlist.py -l "Music" -f "chill.m3u" -u @all -p /media/Music/

"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from os import path

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"https://{plex_ip}:{plex_port}"

def m3u_to_playlist(ssn, library_name: str, file_path: str, users: list=['@me'], library_path: str=''):
	# Check for illegal arg parsing
	if not path.isfile(file_path):
		return 'File not found'

	# Get tokens of users
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers').text
	user_data = dict(map(lambda r: r.split('"')[0:7:6], shared_users.split('username="')[1:]))
	user_data['@me'] = plex_api_token
	if not '@all' in users:
		user_data = {k: v for k, v in user_data.items() if k in users}

	# Loop through the libraries
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory', [])
	for lib in sections:
		if lib['title'] == library_name:
			for user_token in user_data.values():
				ssn.post(f'{base_url}/playlists/upload', params={'sectionID': lib['key'], 'path': library_path+file_path, 'X-Plex-Token': user_token})
			return

	return 'Library not found'

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	# Setup arg parsing
	parser = ArgumentParser(description='Convert a .m3u file to a plex playlist')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library', required=True)
	parser.add_argument('-p','--LibraryPath', type=str, help='Path within Plex to the Music files. Make sure it ends with /.', default='', required=False)
	parser.add_argument('-f','--File', type=str, help="File path to the .m3u file", required=True)
	parser.add_argument('-u','--User', help='Apply user-specific sync actions to these users; This argument can be given multiple times; Use @me to target yourself; Use @all to target everyone', action='append', default=['@me'])

	args = parser.parse_args()
	# Call function and process result
	response = m3u_to_playlist(ssn=ssn, library_name=args.LibraryName, file_path=args.File, users=args.User, library_path=args.LibraryPath)
	if response is not None:
		parser.error(response)
