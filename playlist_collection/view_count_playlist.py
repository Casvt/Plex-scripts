#!/usr/bin/python3
#The use case of this script is the following:
#	Remove entries in a playlist when they've met or surpassed the given viewcount

plex_ip = ''
plex_port = ''
plex_api_token = ''

import sys
import getopt
import requests
import json
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
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
baseurl = 'http://' + plex_ip + ':' + plex_port

arguments, values = getopt.getopt(sys.argv[1:], 'p:c:', ['PlaylistName=', 'ViewCount='])
playlist_id = ''
viewcount = ''
for argument, value in arguments:
	if argument in ('-p', '--PlaylistName'):
		for level in json.loads(ssn.get(baseurl + '/playlists').text)['MediaContainer']['Metadata']:
			if level['title'] == value: playlist_id = level['ratingKey']
		if not playlist_id:
			print('Playlist not found')
			exit(1)
	if argument in ('-c', '--ViewCount'):
		if re.search('^\d+', value): viewcount = value
		else:
			print(value + 'is not a valid view count')
			exit(1)

if not playlist_id or not viewcount:
	print('Error: Arguments were not all given')
	print('Required: -p/--PlaylistName [name of target playlist], -c/--ViewCount [viewcount to remove entries after]')
	exit(1)

for entry in json.loads(ssn.get(baseurl + '/playlists/' + str(playlist_id) + '/items').text)['MediaContainer']['Metadata']:
	#do this for every entry in the playlist
	if int(entry['viewCount']) >= int(viewcount):
		#the entry's viewcount has surpassed the allowed count; remove it
		ssn.delete(baseurl + '/playlists/' + str(playlist_id) + '/items/' + str(entry['playlistItemID']))
