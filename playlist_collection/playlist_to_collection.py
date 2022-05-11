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

from os import getenv

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def playlist_to_collection(ssn, library_name: str, playlist_name: str, remove_playlist: bool=False):
	result_json = []

	#get playlist info
	playlists = ssn.get(f'{base_url}/playlists').json()['MediaContainer']
	if not 'Metadata' in playlists: return 'Playlist not found'
	#loop through every playlist
	for playlist in playlists['Metadata']:
		if playlist['title'] == playlist_name:
			#playlist found
			playlist_id = playlist['ratingKey']
			playlist_entries = ssn.get(f'{base_url}/playlists/{playlist["ratingKey"]}/items').json()['MediaContainer']
			if not 'Metadata' in playlist_entries:
				return 'Playlist is empty'
			else:
				playlist_entries = [entry['ratingKey'] for entry in playlist_entries['Metadata']]
			break
	else:
		return 'Playlist not found'

	#get library info
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through every library
	for lib in sections:
		if lib['title'] == library_name:
			#library found
			lib_id = lib['key']
			if lib['type'] == 'movie': lib_type = '1'
			elif lib['type'] == 'show': lib_type = '4'
			elif lib['type'] == 'artist': lib_type = '10'
			elif lib['type'] == 'photo': lib_type = '13'
			else: return 'Library type not supported'
			break
	else:
		return 'Library not found'

	#remove already existing collection with same name
	collections = ssn.get(f'{base_url}/library/sections/{lib_id}/collections').json()['MediaContainer']
	if 'Metadata' in collections:
		for collection in collections['Metadata']:
			if collection['title'] == playlist_name:
				ssn.delete(f'{base_url}/library/collections/{collection["ratingKey"]}')
				break
	
	#create new collection
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	ssn.post(f'{base_url}/library/collections', params={'type': lib_type, 'title': playlist_name, 'smart': '0', 'sectionId': lib_id, 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(playlist_entries)}'})
	if remove_playlist == True:
		ssn.delete(f'{base_url}/playlists/{playlist_id}')

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Get the content of a playlist and put it in a collection')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library', required=True)
	parser.add_argument('-p','--PlaylistName', type=str, help='Name of target playlist', required=True)
	parser.add_argument('-r','--RemovePlaylist', help='Remove source playlist afterwards', action='store_true')

	args = parser.parse_args()
	#call function and process result
	response = playlist_to_collection(ssn=ssn, library_name=args.LibraryName, playlist_name=args.PlaylistName, remove_playlist=args.RemovePlaylist)
	if not isinstance(response, list):
		parser.error(response)
