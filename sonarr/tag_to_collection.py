#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Put all movies (radarr) or series (sonarr) with a certain tag in a collection in plex
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

#These need to be filled when you want to use the script with sonarr
sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''

#These need to be filled when you want to use the script with radarr
radarr_ip = ''
radarr_port = ''
radarr_api_token = ''

from os import getenv
import requests

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f'http://{plex_ip}:{plex_port}'
sonarr_ip = getenv('sonarr_ip', sonarr_ip)
sonarr_port = getenv('sonarr_port', sonarr_port)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
radarr_ip = getenv('radarr_ip', radarr_ip)
radarr_port = getenv('radarr_port', radarr_port)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)

def _find_in_plex(plex_ssn, path: str, sections: list):
	#find library that file is in
	for lib in sections:
		for loc in lib['Location']:
			if loc['path'] in path:
				lib_id = lib['key']
				content_type = '1' if lib['type'] == 'movie' else '4'
				break
		else:
			continue
		break
	else:
		return ''

	#find file in library
	lib_output = plex_ssn.get(f'{base_url}/library/sections/{lib_id}/all', params={'type': content_type}).json()['MediaContainer']['Metadata']
	for entry in lib_output:
		for media in entry['Media']:
			for part in media['Part']:
				if path in part['file']:
					return entry['grandparentRatingKey']
	return ''

def tag_to_collection(plex_ssn, source: str, tag_name: str, library_name: str, collection_name: str):
	result_json = []

	sections = plex_ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	for lib in sections:
		if lib['title'] == library_name:
			lib_id = lib['key']
			break
	else:
		return 'Library not found'

	if source == 'sonarr':
		if sonarr_ip and sonarr_port and sonarr_api_token:
			#apply script to sonarr
			sonarr_base_url = f'http://{sonarr_ip}:{sonarr_port}/api/v3'
			sonarr_ssn = requests.Session()
			sonarr_ssn.params.update({'apikey': sonarr_api_token})
			try:
				series_list = sonarr_ssn.get(f'{sonarr_base_url}/series').json()
			except requests.exceptions.ConnectionError:
				return 'Can\'t connect to Sonarr'

			#find id of tag
			tags = sonarr_ssn.get(f'{sonarr_base_url}/tag').json()
			for tag in tags:
				if tag['label'] == tag_name:
					tag_id = tag['id']
					break
			else:
				return 'Tag not found'

			#loop through all series in sonarr
			for series in series_list:
				if tag_id in series['tags']:
					#series found with tag applied
					result_json.append(_find_in_plex(plex_ssn=plex_ssn, path=series['path'], sections=sections))
#delete prev collection with name
#create collection
#add ratingkeys to result_json
		else:
			return 'Sonarr set as source but variables not set'

	elif source == 'radarr':
		if radarr_ip and radarr_port and radarr_api_token:
			#apply script to sonarr
			radarr_base_url = f'http://{radarr_ip}:{radarr_port}/api/v3'
			radarr_ssn = requests.Session()
			radarr_ssn.params.update({'apikey': radarr_api_token})
			try:
				movie_list = radarr_ssn.get(f'{radarr_base_url}/movie').json()
			except requests.exceptions.ConnectionError:
				return 'Can\'t connect to Radarr'

			#find id of tag
			tags = radarr_ssn.get(f'{radarr_base_url}/tag')
			for tag in tags:
				if tag['label'] == tag_name:
					tag_id = tag['id']
					break
			else:
				return 'Tag not found'

			#loop through all movies in radarr
			for movie in movie_list:
				if tag_id in movie['tags']:
					#series found with tag applied
					result_json.append(_find_in_plex(plex_ssn=plex_ssn, path=movie.get('movieFile','').get('path',''), sections=sections))
		else:
			return 'Radarr set as source but variables not set'

	#delete collection if it already exists
	collections = plex_ssn.get(f'{base_url}/library/sections/{lib_id}/collections').json()['MediaContainer'].get('Metadata',[])
	for collection in collections:
		if collection['title'] == collection_name:
			plex_ssn.delete(f'{base_url}/library/collections/{collection["ratingKey"]}')

	#create collection
	machine_id = plex_ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	plex_ssn.post(f'{base_url}/library/collections', params={'type': '1' if source == 'radarr' else '2', 'title': collection_name, 'smart': '0', 'sectionId': lib_id, 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(result_json)}'})

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	#setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = ArgumentParser(description="Put all movies (radarr) or series (sonarr) with a certain tag in a collection in plex")
	parser.add_argument('-s', '--Source', type=str, choices=['sonarr','radarr'], help="Select the source which media files should be checked", required=True)
	parser.add_argument('-t', '--TagName', type=str, help="Name of tag to search for", required=True)
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of the target library to put the collection in", required=True)
	parser.add_argument('-c', '--CollectionName', type=str, help="Name of the collection", required=True)

	args = parser.parse_args()
	#call function and process result
	response = tag_to_collection(plex_ssn=ssn, source=args.Source, tag_name=args.TagName, library_name=args.LibraryName, collection_name=args.CollectionName)
	if not isinstance(response, list):
		parser.error(response)
