#The use case of this script is the following:
#	After you've selected a movie library, it will try to set the audio track to one with the desired amount of channels
#	if it was not already. It will do it for every movie inside that library.

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
arguments, values = getopt.getopt(sys.argv[1:], 'l:c:', ['LibraryName=', 'Channels='])
lib_id = ''
channels = ''
for argument, value in arguments:
	if argument in ('-l', '--LibraryName'):
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == value and level['type'] == 'movie': lib_id = level['key']
		if not lib_id:
			print('Library not found or not a movie library')
			exit(1)
	if argument in ('-c', '--Channels'):
		if re.search('^\d+', value): channels = value
		else:
			print(value + 'is not a valid channel count')
			exit(1)

if not lib_id or not channels:
	print('Error: Arguments were not all given')
	print('Required: -l/--LibraryName [name of target library], -c/--Channels [channel count]')
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
		for stream in part_db[part]['Stream']:
			if stream['streamType'] == 2 and int(stream['channels']) == int(channels) and not 'selected' in stream.keys():
				print('	Upgraded')
				ssn.put('http://' + plex_ip + ':' + plex_port + '/library/parts/' + str(part), params={'audioStreamID': stream['id'], 'allParts': 1})
				break
