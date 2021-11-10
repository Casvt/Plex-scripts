#!/usr/bin/python3

#The use case of this scriot is the following:
#	get the content of a playlist and put it in a collection

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests
import getopt
import sys
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

ssn = requests.Session()
ssn.headers.update({"accept": "application/json"})
ssn.params.update({"X-Plex-Token": plex_api_token})
baseurl = 'http://' + plex_ip + ':' + plex_port

section_output = ssn.get(baseurl + '/library/sections').json()
playlists_output = ssn.get(baseurl + '/playlists').json()
arguments, values = getopt.getopt(sys.argv[1:], 'l:p:r', ['TargetLibraryName=', 'PlaylistName=', 'RemovePlaylist'])
lib_id = ''
playlist_id = ''
remove_playlist = False
for argument, value in arguments:
	if argument in ('-l', '--LibraryName'):
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == value: lib_id = level['key']
		if not lib_id:
			print('Library not found')
			exit(1)
	if argument in ('-p', '--PlaylistName'):
		for level in playlists_output['MediaContainer']['Metadata']:
			if level['title'] == value:
				playlist_id = level['ratingKey']
				playlist_name = value
		if not playlist_id:
			print('Playlist not found')
			exit(1)
	if argument in ('-r', '--RemovePlaylist'):
		remove_playlist = True

if not lib_id or not playlist_id:
	print('Error: Arguments were not all given')
	print('Required: -l/--LibraryName [name of library to put collection in], -p/--PlaylistName [name of the playlist to copy/move]')
	print('Optional: -r/--RemovePlaylist\n		After copying the contents of the playlist to the collection, you can remove the playlist with this flag')
	exit(1)

for entry in ssn.get(baseurl + '/library/sections/' + lib_id + '/collections').json()['MediaContainer']['Metadata']:
	if entry['title'] == playlist_name:
		ssn.delete(baseurl + '/library/collections/' + entry['ratingKey'])

entries = []
for entry in ssn.get(baseurl + '/playlists/' + str(playlist_id) + '/items').json()['MediaContainer']['Metadata']:
	entries.append(entry['ratingKey'])

machine_id = ssn.get(baseurl + '/').json()['MediaContainer']['machineIdentifier']
ssn.post(baseurl + '/library/collections', params={'type': '1', 'title': playlist_name, 'smart': '0', 'sectionId': str(lib_id), 'uri': 'server://' + machine_id + '/com.plexapp.plugins.library/library/metadata/' + ','.join(entries)})
if remove_playlist:
	ssn.delete(baseurl + '/playlists/' + playlist_id)
