#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Create a playlist for every sub-folder in a library containing the media in it
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import os

# Environmental Variables
plex_ip = os.getenv('plex_ip', plex_ip)
plex_port = os.getenv('plex_port', plex_port)
plex_api_token = os.getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def sub_folder_playlists(ssn, library_folder: str):
	result_json = []

	if not os.path.isdir(library_folder):
		return 'Folder not found'

	#find library of folder
	library_folder = library_folder.rstrip('/')
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	for lib in sections:
		for loc in lib['Location']:
			if loc['path'].rstrip('/') == library_folder:
				lib_id = lib['key']
				content_type = '1' if lib['type'] == 'movie' else '4'
				break
		else:
			continue
		break
	else:
		return 'Library not found'

	#get subfolders of library
	sub_folders = [d for d in os.listdir(library_folder) if os.path.isdir(os.path.join(library_folder, d))]

	#get lib content
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	lib_content = ssn.get(f'{base_url}/library/sections/{lib_id}/all', params={'type': content_type}).json()['MediaContainer']['Metadata']
	for entry in lib_content:
		for sub_folder in sub_folders:
			if os.path.join(library_folder, sub_folder) in entry['Media'][0]['Part'][0]['file']:
				#media is in subfolder so add it to playlist
				playlists = ssn.get(f'{base_url}/playlists', params={'playlistType': 'video'}).json()['MediaContainer']
				if not 'Metadata' in playlists: playlists['Metadata'] = []
				for playlist in playlists:
					if playlist['title'] == sub_folder:
						#playlist found; add media to it
						ssn.put(f'{base_url}/playlists/{playlist["ratingKey"]}/items', params={'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{entry["ratingKey"]}'})
						break
				else:
					#create playlist
					ssn.post(f'{base_url}/playlists', params={'type': 'video', 'title': sub_folder, 'smart': '0', 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{entry["ratingKey"]}'})

				result_json.append(entry['ratingKey'])
				break

	return result_json

if __name__ == '__main__':
	import argparse, requests

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept':'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Create a playlist for every sub-folder in a library containing the media in it')
	parser.add_argument('-f','--LibraryFolder', type=str, help="Give the path to the root-folder of the library that the script should target", required=True)

	args = parser.parse_args()
	#call function and process result
	response = sub_folder_playlists(ssn=ssn, library_folder=args.LibraryFolder)
	if not isinstance(response, list):
		parser.error(response)

