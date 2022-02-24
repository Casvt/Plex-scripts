#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Get the content of a playlist and put it in a collection
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests, argparse

ssn = requests.Session()
ssn.headers.update({"accept": "application/json"})
ssn.params.update({"X-Plex-Token": plex_api_token})
baseurl = f'http://{plex_ip}:{plex_port}'

parser = argparse.ArgumentParser(description="Get the content of a playlist and put it in a collection")
parser.add_argument('-l','--LibraryName', help="Name of library to put collection in", required=True)
parser.add_argument('-p','--PlaylistName', help="Name of playlist to get the content from", required=True)
parser.add_argument('-r','--RemovePlaylist', help="Remove playlist after creating collection", action='store_true')
args = parser.parse_args()

#gather info about library, playlist and server
machine_id = ssn.get(f'{baseurl}/').json()['MediaContainer']['machineIdentifier']
section_output = ssn.get(f'{baseurl}/library/sections').json()
playlists_output = ssn.get(f'{baseurl}/playlists').json()
for lib in section_output['MediaContainer']['Directory']:
	if lib['title'] == args.LibraryName:
		lib_id = lib['key']
		if lib['type'] == 'movie': lib_type = '1'
		elif lib['type'] == 'show': lib_type = '4'
		elif lib['type'] == 'artist': lib_type = '10'
		elif lib['type'] == 'photo': lib_type = '13'
		break
else: parser.error('Library not found')

for playlist in playlists_output['MediaContainer']['Metadata']:
	if playlist['title'] == args.PlaylistName:
		playlist_id = playlist['ratingKey']
		break
else: parser.error('Playlist not found')

#remove already existing collection with the name
collections = ssn.get(f'{baseurl}/library/sections/{lib_id}/collections').json()
if collections['MediaContainer']['size'] > 0:
	for entry in collections['MediaContainer']['Metadata']:
		if entry['title'] == args.PlaylistName:
			ssn.delete(f'{baseurl}/library/collections/{entry["ratingKey"]}')
			break

#create list of items that should be added to the collection, sourced from the playlist
entries = [entry['ratingKey'] for entry in ssn.get(f'{baseurl}/playlists/{playlist_id}/items').json()['MediaContainer']['Metadata']]

#create collection with the list of items
ssn.post(f'{baseurl}/library/collections', params={'type': lib_type, 'title': args.PlaylistName, 'smart': '0', 'sectionId': str(lib_id), 'uri': 'server://' + machine_id + '/com.plexapp.plugins.library/library/metadata/' + ','.join(entries)})
if args.RemovePlaylist == True:
	ssn.delete(f'{baseurl}/playlists/{playlist_id}')
