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
arguments, values = getopt.getopt(sys.argv[1:], 'n:l:', ['LibraryName=', 'Language='])
lib_id = ''
lang = ''
for argument, value in arguments:
	if argument in ('-n', '--LibraryName'):
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == value and level['type'] == 'movie': lib_id = level['key']
		if not lib_id:
			print('Library not found or not a movie library')
			exit(1)
	if argument in ('-l', '--Language'):
		if re.search('^.{1,5}$', value): lang = value
		else:
			print(value + 'is not a valid language code')
			exit(1)

if not lib_id or not lang:
	print('Error: Arguments were not all given')
	print('Required: -n/--LibraryName [name of target library], -l/--Language [language code (2 letters)]')
	exit(1)

for movie in json.loads(ssn.get('http://' + plex_ip + ':' + plex_port + '/library/sections/' + lib_id + '/all').text)['MediaContainer']['Metadata']:
	part_id = []
	part_db = {}
	key = movie['key']
	movie_output = json.loads(ssn.get('http://' + plex_ip + ':' + plex_port + key).text)
	print(movie_output['MediaContainer']['Metadata'][0]['title'])
	for media in movie_output['MediaContainer']['Metadata'][0]['Media']:
		for part in media['Part']:
			part_db[part['id']] = part
			part_id.append(part['id'])
	for part in part_id:
		selected_stream = ''
		for stream in part_db[part]['Stream']:
			if stream['streamType'] == 2 and 'selected' in stream.keys() and 'languageTag' in stream.keys() and stream['languageTag'] == lang:
				selected_stream = stream
				break
		for stream in part_db[part]['Stream']:
			if stream['streamType'] == 2 and 'languageTag' in stream.keys() and stream['languageTag'] == lang and not selected_stream:
				print('	Upgraded')
				ssn.put('http://' + plex_ip + ':' + plex_port + '/library/parts/' + str(part), params={'audioStreamID': stream['id'], 'allParts': 1})
				break
