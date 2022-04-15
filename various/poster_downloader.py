#!/usr/bin/python3

#The use case of this script is the following:
#	Download the poster of every entry in the library that you give to the destination foldr (.png)

plex_ip = ''
plex_port = ''
plex_api_token = ''

import re
import json
import requests
import sys
import getopt
import os

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
baseurl = 'http://' + plex_ip + ':' + plex_port

section_output = json.loads(ssn.get(baseurl + '/library/sections').text)
arguments, values = getopt.getopt(sys.argv[1:], 'l:o:', ['LibraryName=', 'OutputPath='])
lib_id = ''
output_path = ''
for argument, value in arguments:
	if argument in ('-l', '--LibraryName'):
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == value:
				if level['type'] == 'movie' or level['type'] == 'show':
					lib_id = level['key']
		if not lib_id:
			print('Library not found or not a movie/show library')
			exit(1)
	if argument in ('-o', '--OutputPath'):
		if os.path.exists(value): output_path = value
		else:
			print('Output path not found')
			exit(1)

if not lib_id or not output_path:
	print('Error: Arguments were not all given')
	print('Required: -l/--LibraryName [name of target library], -o/--OutputPath [path to folder where posters are going to be put]')
	exit(1)

lib_output = json.loads(ssn.get(baseurl + '/library/sections/' + lib_id + '/all').text)
for level in lib_output['MediaContainer']['Metadata']:
	#do this for every entry in the library
	print(level['title'])
	poster_output = json.loads(ssn.get(baseurl + '/library/metadata/' + level['ratingKey'] + '/posters').text)
	for poster in poster_output['MediaContainer']['Metadata']:
		#do this for every available poster of the entry
		if poster['selected'] == True:
			#download the poster to the OutputPath
			file = open(os.path.join(output_path, level['title'] + '.png'), 'wb')
			file.write(ssn.get(baseurl + poster['key']).content)
			file.close()
