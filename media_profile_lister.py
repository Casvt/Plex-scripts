plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests
import json
import re
import getopt, sys

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', plex_ip):
	print("Error: " + plex_ip + " is not a valid ip")
	exit(1)

if not re.search('^\d{1,5}$', plex_port):
	print("Error: " + plex_port + " is not a valid port")
	exit(1)

if not re.search('^[\w\d_-~]{19,21}$', plex_api_token):
	print("Error: " + plex_api_token + " is not a valid api token")
	exit(1)

ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})

section_output = json.loads(ssn.get('http://' + plex_ip + ':' + plex_port + '/library/sections').text)
arguments, values = getopt.getopt(sys.argv[1:], 'l:p:', ['LibraryName=', 'Profile='])
lib_id = ''
lib_type = ''
profile = ''
for argument, value in arguments:
	if argument in ('-l', '--LibraryName'):
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == value:
				if level['type'] == 'movie' or level['type'] == 'show':
					lib_id = level['key']
					lib_type = level['type']
		if not lib_id:
			print('Library not found or not a movie library')
			exit(1)
	if argument in ('-p', '--Profile'): profile = value

if not lib_id or not profile:
	print('Error: Arguments were not all given')
	print('Required: -l/--LibraryName [name of target library], -p/--Profile [profile of media to show (e.g. \'main 10\')]')
	exit(1)

if lib_type == 'movie':
	for movie in json.loads(ssn.get('http://' + plex_ip + ':' + plex_port + '/library/sections/' + lib_id + '/all').text)['MediaContainer']['Metadata']:
		if 'videoProfile' in movie['Media'][0] and movie['Media'][0]['videoProfile'] == profile: print(movie['title'])
elif lib_type == 'show':
	for show in json.loads(ssn.get('http://' + plex_ip + ':' + plex_port + '/library/sections/' + lib_id + '/all').text)['MediaContainer']['Metadata']:
		show_key = show['key']
		for season in json.loads(ssn.get('http://' + plex_ip + ':' + plex_port + show_key).text)['MediaContainer']['Metadata']:
			season_key = season['key']
			for episode in json.loads(ssn.get('http://' + plex_ip + ':' + plex_port + season_key).text)['MediaContainer']['Metadata']:
				if 'videoProfile' in episode['Media'][0] and episode['Media'][0]['videoProfile'] == profile: print(episode['grandparentTitle'] + ' - S' + str(episode['parentIndex']) + 'E' + str(episode['index']) + ' - ' + str(episode['title']))
