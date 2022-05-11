#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Remove entries in a playlist when they've met or surpassed the given viewcount
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every 20m or every 12h)
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

def view_count_playlist(ssn, playlist_name: str, view_count: int):
	result_json = []

	playlists = ssn.get(f'{base_url}/playlists').json()['MediaContainer']
	if not 'Metadata' in playlists: return 'Playlist not found'
	#loop through every playlist
	for playlist in playlists['Metadata']:
		if playlist['title'] == playlist_name:
			#playlist found
			playlist_entries = ssn.get(f'{base_url}/playlists/{playlist["ratingKey"]}/items').json()['MediaContainer']
			if not 'Metadata' in playlist_entries: return result_json
			#loop through every entry in the playlist
			for entry in playlist_entries['Metadata']:
				if 'viewCount' in entry and int(entry['viewCount']) >= view_count:
					#entry surpassed view count so remove it
					result_json.append(entry['ratingKey'])
					ssn.delete(f'{base_url}/playlists/{playlist["ratingKey"]}/items/{entry["playlistItemID"]}')
			break
	else:
		return 'Playlist not found'

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Remove entries in a playlist when they\'ve met or surpassed the given viewcount')
	parser.add_argument('-p','--PlaylistName', type=str, help='Name of target playlist', required=True)
	parser.add_argument('-c','--ViewCount', type=int, help='The viewcount that is the minimum to be removed', required=True)

	args = parser.parse_args()
	#call function and process result
	response = view_count_playlist(ssn=ssn, playlist_name=args.PlaylistName, view_count=args.ViewCount)
	if not isinstance(response, list):
		parser.error(response)
