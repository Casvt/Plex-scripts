#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Make a collection with the top 10 most popular movies according to tautulli
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every 20m or every 12h)
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

tautulli_ip = ''
tautulli_port = ''
tautulli_api_token = ''

from os import getenv
import requests

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
plex_base_url = f"http://{plex_ip}:{plex_port}"
tautulli_ip = getenv('tautulli_ip', tautulli_ip)
tautulli_port = getenv('tautulli_port', tautulli_port)
tautulli_api_token = getenv('tautulli_api_token', tautulli_api_token)
tautulli_base_url = f"http://{tautulli_ip}:{tautulli_port}/api/v2"

def top10_collection(ssn, library_name: str, collection_title: str):
	result_json = []

	sections = ssn.get(f'{plex_base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] == library_name:
			#library found
			lib_collections = ssn.get(f'{plex_base_url}/library/sections/{lib["key"]}/collections').json()['MediaContainer']
			if 'Metadata' in lib_collections:
				#delete old version of collection if present
				for collection in lib_collections['Metadata']:
					if collection['title'] == collection_title:
						collection_id = collection['ratingKey']
						ssn.delete(f'{plex_base_url}/library/collections/{collection_id}')
						break

			#get new list of top movies
			movies = requests.get(f'{tautulli_base_url}', params={'apikey': tautulli_api_token, 'cmd': 'get_home_stats', 'stat_id': 'top_movies'}).json()['response']['data']['rows']
			movie_ratingkeys = [str(movie['rating_key']) for movie in movies]
			result_json = movie_ratingkeys

			#create new collection
			machine_id = ssn.get(f'{plex_base_url}/').json()['MediaContainer']['machineIdentifier']
			ssn.post(f'{plex_base_url}/library/collections', params={'type': 1, 'title': collection_title, 'smart': 0, 'sectionId': lib['key'], 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(movie_ratingkeys)}'})
			break
	else:
		return 'Library not found'

	return result_json

if __name__ == '__main__':
	import argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Make a collection with the top 10 most popular movies according to tautulli')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library', required=True)
	parser.add_argument('-t','--CollectionTitle', type=str, help='The title of the collection', default='Top 10 movies')

	args = parser.parse_args()
	#call function and process result
	response = top10_collection(ssn=ssn, library_name=args.LibraryName, collection_title=args.CollectionTitle)
	if not isinstance(response, list):
		parser.error(response)
