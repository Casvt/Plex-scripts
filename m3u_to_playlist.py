#used for converting an m3u file to a plex playlist

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests
import json
import getopt, sys
import os
import re

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', plex_ip):
	print("Error: " + plex_ip + " is not a valid ip")
	exit(1)

if not re.search('^\d{1,5}$', plex_port):
	print("Error: " + plex_port + " is not a valid port")
	exit(1)

if not re.search('^[\w\d_-~]{19,21}$', plex_api_token):
	print("Error: " + plex_api_token + " is not a valid api token")
	exit(1)

section_output = json.loads(requests.get('http://' + plex_ip + ':' + plex_port + '/library/sections', params={'X-Plex-Token': plex_api_token}, headers={'Accept': 'application/json'}).text)
arguments, values = getopt.getopt(sys.argv[1:], 'l:f:', ['LibraryName =', 'File ='])
for argument, value in arguments:
	if argument in ('-l', '--LibraryName'):
		lib_id = ''
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == value: lib_id = level['key']
		if not lib_id:
			print('Library not found')
			exit(1)
	if argument in ('-f', '--File'):
		file_path = value
		if not os.path.exists(value):
			print('File not found')
			exit(1)

requests.post('http://' + plex_ip + ':' + plex_port + '/playlists/upload', params={'X-Plex-Token': plex_api_token, 'sectionID': lib_id, 'path': file_path})
