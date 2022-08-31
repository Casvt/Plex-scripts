#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Create an empty collection. It will be a non-smart collection without any content.
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from os.path import isfile

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

media_types = {
	'movie': (1,1),
	'show': (2,4),
	'artist': (8,10)
}

def create_empty_collection(ssn, library_name: str, title: str, summary: str='', poster: str='', background: str='', sort_title: str='', delete_existing: bool=False):
	result_json = []

	#check if library exists
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	for lib in sections:
		if lib['title'] == library_name:
			lib_id = lib['key']
			lib_type = lib['type']
			break
	else:
		return 'Library not found'

	if delete_existing == True:
		collections = ssn.get(f'{base_url}/library/sections/{lib_id}/collections').json()['MediaContainer'].get('Metadata',[])
		for collection in collections:
			if collection['title'] == title:
				ssn.delete(f'{base_url}/library/collections/{collection["ratingKey"]}')

	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	#create collection
	new_ratingkey = ssn.post(f'{base_url}/library/collections', params={'title': title, 'smart': '0', 'sectionId': lib_id, 'type': media_types[lib_type][1], 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/'}).json()['MediaContainer']['Metadata'][0]['ratingKey']
	result_json.append(new_ratingkey)

	if poster != '':
		#set poster
		if isfile(poster):
			data = open(poster, 'rb').read()
		elif poster.startswith('http'):
			data = ssn.get(poster).content
		else:
			return 'Poster file not found or url not valid'

		ssn.post(f'{base_url}/library/collections/{new_ratingkey}/posters', data=data)

	if background != '':
		#set background
		if isfile(background):
			data = open(background, 'rb').read()
		elif background.startswith('http'):
			data = ssn.get(background).content
		else:
			return 'Background file not found or url not valid'

		ssn.post(f'{base_url}/library/collections/{new_ratingkey}/arts', data=data)

	if summary != '' or sort_title != '':
		#set settings
		payload = {
			'type': 18,
			'id': new_ratingkey,
		}
		if summary != '':
			payload['summary.value'] = summary
			payload['summary.locked'] = 1
		if sort_title != '':
			payload['titleSort.value'] = sort_title
			payload['titleSort.locked'] = 1

		ssn.put(f'{base_url}/library/sections/{lib_id}/all', params=payload)

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Create an empty collection. It will be a non-smart collection without any content.')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library to put collection in', required=True)
	parser.add_argument('-t','--Title', type=str, help='Name of collection', required=True)
	parser.add_argument('-s','--Summary', type=str, help='Summary of the collection', default='')
	parser.add_argument('-p','--Poster', type=str, help='URL or filepath to image that will be set as the poster', default='')
	parser.add_argument('-b','--Background', type=str, help='URL or filepath to image that will be set as the background', default='')
	parser.add_argument('-S','--SortTitle', type=str, help='The sort title of the collection', default='')
	parser.add_argument('-D','--DeleteExisting', action='store_true', help='If a collection with the same name already exists, delete it first')

	args = parser.parse_args()
	#call function and process result
	response = create_empty_collection(ssn=ssn, library_name=args.LibraryName, title=args.Title, summary=args.Summary, poster=args.Poster, background=args.Background, sort_title=args.SortTitle, delete_existing=args.DeleteExisting)
	if not isinstance(response, list):
		parser.error(response)
