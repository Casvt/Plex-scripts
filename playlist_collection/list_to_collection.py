#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Give the id of a IMDb list and make a collection in plex of the movies in the list
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from re import findall as re_findall

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def list_to_collection(ssn, source: str, list_id: str, library_name: str):
	result_json = []

	#check for illegal argument parsing
	if not source in ('IMDb'):
		return 'Invalid value for "source"'

	#get list of source id's
	if source == 'IMDb':
		r = ssn.get(f'https://www.imdb.com/list/{list_id}')
		if r.status_code != 200:
			return 'List not found'
		list_content = r.text
		list_title = re_findall(r'(?<=<h1 class="header list-name">).*?(?=</h1>)', list_content)[0]
		list_ids = ['imdb://' + t.split('"')[-1] for t in re_findall(r'<div class="lister-item mode-detail">\n\s+?<div.*?data-tconst="tt\d+', list_content)]
		if not list_ids: return 'No media in list found'

	print(list_title)

	#find id of target library
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] != library_name: continue
		#this library is targeted
		lib_id = lib['key']
		if lib['type'] == 'movie': 
			lib_type = '1'
			collection_type = '1'
		elif lib['type'] == 'show':
			lib_type = '4'
			collection_type = '2'
		break
	else:
		return 'Library not found'

	#find media in library
	lib_output = ssn.get(f'{base_url}/library/sections/{lib_id}/all', params={'type': lib_type, 'includeGuids': '1'}).json()['MediaContainer']['Metadata']
	for guid in list_ids:
		for media in lib_output:
			for id in media.get('Guid',[]):
				if id['id'] == guid:
					break
			else:
				continue
			result_json.append(media['ratingKey'])
			break

	#delete collection if it already exists
	lib_collections = ssn.get(f'{base_url}/library/sections/{lib_id}/collections').json()['MediaContainer'].get('Metadata',[])
	for collection in lib_collections:
		if collection['title'] == list_title:
			ssn.delete(f'{base_url}/library/collections/{collection["ratingKey"]}')
	
	#create new collection
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	ssn.post(f'{base_url}/library/collections', params={'title': list_title, 'smart': '0', 'sectionId': lib_id, 'type': collection_type, 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(result_json)}'})

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	#setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = ArgumentParser(description='Give the id of a IMDb list and make a collection in plex of the movies in the list')
	parser.add_argument('-s','--Source', choices=['IMDb'], help='The source of the list', required=True)
	parser.add_argument('-i','--Id', type=str, help='The id of the list', required=True)
	parser.add_argument('-l','--LibraryName', type=str, help='Name of library to put collection in', required=True)

	args = parser.parse_args()
	#call function and process result
	response = list_to_collection(ssn=ssn, source=args.Source, list_id=args.Id, library_name=args.LibraryName)
	if not isinstance(response, list):
		parser.error(response)
