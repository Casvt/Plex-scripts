#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Create a collection containing all the movies of the x first actors (and optionally of the movie director) of the last viewed movie
	The collection will be put in the library from where the source movie originated
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every 5m)
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

def actor_collection(ssn, collection_name: str='Actor Collection', actors: int=5, movie_director: bool=False):
	result_json = []

	#search in history for last viewed movie
	history = ssn.get(f'{base_url}/status/sessions/history/all').json()['MediaContainer']
	if not 'Metadata' in history: return result_json
	for media in history['Metadata'][::-1]:
		if media['type'] == 'movie':
			#found last viewed movie
			media_info = ssn.get(f'{base_url}/library/metadata/{media["ratingKey"]}').json()['MediaContainer']['Metadata'][0]
			if not 'Role' in media_info: continue

			#get the ids of the actors to get the movies of
			actor_ids = [a['id'] for a in media_info['Role'][0:actors]]
			#note the movies down that the actors played in
			movie_ratingkeys = []
			for actor in actor_ids:
				actor_movies = ssn.get(f'{base_url}/library/sections/{media["librarySectionID"]}/all', params={'type': '1', 'actor': actor}).json()['MediaContainer']['Metadata']
				movie_ratingkeys += [m['ratingKey'] for m in actor_movies if not m['ratingKey'] in movie_ratingkeys]

			if movie_director == True:
				#get the movies of the movie director too
				director_movies = ssn.get(f'{base_url}/library/sections/{media["librarySectionID"]}/all', params={'type': '1',  'director': media_info['Director'][0]['id']}).json()['MediaContainer']['Metadata']
				movie_ratingkeys += [m['ratingKey'] for m in director_movies if not m['ratingKey'] in movie_ratingkeys]
			
			#if collection with this name already exists, remove it first
			collections = ssn.get(f'{base_url}/library/sections/{media["librarySectionID"]}/collections').json()['MediaContainer']['Metadata']
			for collection in collections:
				if collection['title'] == collection_name:
					ssn.delete(f'{base_url}/library/collections/{collection["ratingKey"]}')
			
			#create collection
			machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
			ssn.post(f'{base_url}/library/collections', params={'type': '1', 'title': collection_name, 'smart': '0', 'sectionId': media['librarySectionID'], 'uri': f'server://{machine_id}/com.plexapp.library/library/metadata/{",".join(movie_ratingkeys)}'})
			result_json = movie_ratingkeys
			break

	return result_json

if __name__  == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Create a collection containing all the movies of the x first actors (and optionally of the movie director) of the last viewed movie')
	parser.add_argument('-c','--CollectionName', type=str, help='Name of target collection', default='Actor Collection')
	parser.add_argument('-a','--Actors', type=int, help="How many of the movie actors should be looked at to take the movies from to include them in the collection", default=5)
	parser.add_argument('-d','--MovieDirector', help="Also include all the movies of the director in the collection", action="store_true")

	args = parser.parse_args()
	#call function and process result
	response = actor_collection(ssn=ssn, collection_name=args.CollectionName, actors=args.Actors, movie_director=args.MovieDirector)
	if not isinstance(response, list):
		parser.error(response)
