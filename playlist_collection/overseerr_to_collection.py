#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Put all requested movies from overseerr in a collection in plex
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

overseerr_ip = ''
overseerr_port = ''
overseerr_api_token = ''

from os import getenv

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
plex_base_url = f"http://{plex_ip}:{plex_port}"
overseerr_ip = getenv('overseerr_ip', overseerr_ip)
overseerr_port = getenv('overseerr_port', overseerr_port)
overseerr_api_token = getenv('overseerr_api_token', overseerr_api_token)
overseerr_base_url = f"http://{overseerr_ip}:{overseerr_port}/api/v1"

def overseerr_to_collection(plex_ssn, overseerr_ssn, library_name: str, collection_name: str='Overseerr requests'):
	result_json = []

	#find plex library
	sections = plex_ssn.get(f'{plex_base_url}/library/sections').json()['MediaContainer']['Directory']
	for lib in sections:
		if lib['title'] == library_name:
			lib_id = lib['key']
			break
	else:
		return 'Library not found'

	#note down plex ratingkey of every requested and downloaded movie in overseerr
	offset = 0
	while 1:
		requests = overseerr_ssn.get(f'{overseerr_base_url}/request', params={'filter': 'available', 'take': 50, 'skip': offset}).json().get('results', [])
		if not requests: break
		for request in requests:
			if request['type'] != 'movie': continue
			if request['media']['ratingKey4k'] != None:
				result_json.append(request['media']['ratingKey4k'])
			elif request['media']['ratingKey'] != None:
				result_json.append(request['media']['ratingKey'])
		offset += 50

	#delete collection if it exists
	collections = plex_ssn.get(f'{plex_base_url}/library/sections/{lib_id}/collections').json()['MediaContainer'].get('Metadata',[])
	for collection in collections:
		if collection == collection_name:
			plex_ssn.delete(f'{plex_base_url}/library/collections/{collection["ratingKey"]}').json()

	#create collection
	machine_id = plex_ssn.get(f'{plex_base_url}/').json()['MediaContainer']['machineIdentifier']
	plex_ssn.post(f'{plex_base_url}/library/collections', params={'title': collection_name, 'smart': '0', 'sectionId': lib_id, 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(result_json)}'})

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	#setup vars
	plex_ssn = Session()
	plex_ssn.headers.update({'Accept': 'application/json'})
	plex_ssn.params.update({'X-Plex-Token': plex_api_token})
	overseerr_ssn = Session()
	overseerr_ssn.headers.update({'X-Api-Key': overseerr_api_token})

	#setup arg parsing
	parser = ArgumentParser(description='Put all requested movies from overseerr in a collection in plex')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target movie library', required=True)
	parser.add_argument('-c','--CollectionName', type=str, help='Name of collection that movies will be put in', default='Overseerr requests')

	args = parser.parse_args()
	#call function and process result
	response = overseerr_to_collection(plex_ssn=plex_ssn, overseerr_ssn=overseerr_ssn, library_name=args.LibraryName, collection_name=args.CollectionName)
	if not isinstance(response, list):
		parser.error(response)
