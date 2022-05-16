#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Add a plex media file to every collection mentioned in the file, split by a '.'
	E.g. Collection1.Collection2.Collection3.mkv
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from os.path import isfile, splitext, basename

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def filename_to_collection(ssn, file_path: str):
	result_json = []

	#check for illegal arg parsing
	if not isfile(file_path):
		return 'File not found'

	#get filename and extract collections
	file_name = splitext(basename(file_path))[0]
	collections = file_name.split('.')

	#find library that file is in
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	for lib in sections:
		for loc in lib['Location']:
			if loc['path'] in file_path:
				lib_id = lib['key']
				content_type = '1' if lib['type'] == 'movie' else '4'
				break
		else:
			continue
		break
	else:
		return 'File not found in any plex library'

	#find file in library
	lib_output = ssn.get(f'{base_url}/library/sections/{lib_id}/all', params={'type': content_type}).json()['MediaContainer']['Metadata']
	for entry in lib_output:
		for media in entry['Media']:
			for part in media['Part']:
				if part['file'] == file_path:
					rating_key = entry['ratingKey']
					break
			else:
				continue
			break
		else:
			continue
		break
	else:
		return 'File not found in any plex library'

	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	lib_collections = ssn.get(f'{base_url}/library/sections/{lib_id}/collections').json()['MediaContainer']['Metadata']
	for lib_collection in lib_collections:
		if lib_collection['title'] in collections:
			#media should be added to this collection
			col_rating_key = ssn.put(f'{base_url}/library/collections/{lib_collection["ratingKey"]}/items', params={'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{rating_key}'}).json()['MediaContainer']['Metadata'][0]['ratingKey']
			collections.pop(lib_collection['title'])
			result_json.append(col_rating_key)

	if collections:
		#one or more collections in the filename don't exist so make them
		for collection_title in collections:
			col_rating_key = ssn.post(f'{base_url}/library/collections', params={'type': content_type, 'title': collection_title, 'smart': '0', 'sectionId': lib_id, 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{rating_key}'}).json()['MediaContainer']['Metadata'][0]['ratingKey']
			result_json.append(col_rating_key)

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Add a plex media file to every collection mentioned in the file, split by a \'.\'')
	parser.add_argument('-f','--FilePath', type=str, help='Path to the media file', required=True)

	args = parser.parse_args()
	#call function and process result
	response = filename_to_collection(ssn=ssn, file_path=args.FilePath)
	if not isinstance(response, list):
		parser.error(response)
