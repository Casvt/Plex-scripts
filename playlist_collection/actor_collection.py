#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Have a collection containing all the movies of the x first actors (and optionally of the movie director) of the last viewed movie
	The collection will be put in the library from where the source movie originated
Requirements (python3 -m pip install [requirement]):
	PlexAPI
	websocket-client
	requests
Setup:
	Once this script is run, it will keep running and will handle the updating of the collection once needed.
	Run it in the background as a service or as a cronjob.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''
collection_name = 'Actor Collection'

import requests, argparse, time
from plexapi.server import PlexServer
#required for alert listener so checking here
import websocket

parser = argparse.ArgumentParser(description='Have a collection containing all the movies of the x first actors (and optionally of the movie director) of the last viewed movie. The collection will be put in the library from where the source movie originated.')
parser.add_argument(
	'-A',
	'--Actors',
	help="How many of the movie actors should be looked at to take the movies from to include them in the collection",
	type=int,
	required=True
)
parser.add_argument(
	'-D',
	'--MovieDirector',
	help="Also include all the movies of the director in the collection",
	action="store_true"
)
args = parser.parse_args()

baseurl = 'http://' + plex_ip + ':' + str(plex_port)
plex = PlexServer(baseurl, plex_api_token)
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})

def process(data):
	if data['PlaySessionStateNotification'][0]['state'] == 'stopped':
		media_output = ssn.get(baseurl + '/library/metadata/' + str(data['PlaySessionStateNotification'][0]['ratingKey'])).json()
		if media_output['MediaContainer']['Metadata'][0]['type'] == 'movie':
			lib_id = str(media_output['MediaContainer']['Metadata'][0]['librarySectionID'])
			actors = []
			actor_movies = []
			for actor in media_output['MediaContainer']['Metadata'][0]['Role']:
				if len(actors) == args.Actors:
					break
				actors.append(actor['id'])
			for actor in actors:
				for actor_movie in ssn.get(baseurl + '/library/sections/' + lib_id + '/all', params={'type': '1', 'actor': actor}).json()['MediaContainer']['Metadata']:
					if not actor_movie['ratingKey'] in actor_movies:
						actor_movies.append(actor_movie['ratingKey'])
			if args.MovieDirector:
				for director_movie in ssn.get(baseurl + '/library/sections/' + lib_id + '/all', params={'type': '1', 'director': media_output['MediaContainer']['Metadata'][0]['Director'][0]['id']}).json()['MediaContainer']['Metadata']:
					if not director_movie['ratingKey'] in actor_movies:
						actor_movies.append(director_movie['ratingKey'])
			col_id = ''
			for collection in ssn.get(baseurl + '/library/sections/' + lib_id + '/collections').json()['MediaContainer']['Metadata']:
				if collection['title'] == collection_name:
					col_id = collection['ratingKey']
			machine_id = ssn.get(baseurl + '/').json()['MediaContainer']['machineIdentifier']
			if col_id:
				ssn.delete(baseurl + '/library/collections/' + col_id)
			ssn.post(baseurl + '/library/collections', params={'type': '1', 'title': collection_name, 'smart': '0', 'sectionId': str(media_output['MediaContainer']['Metadata'][0]['librarySectionID']), 'uri': 'server://' + machine_id + '/com.plexapp.plugins.library/library/metadata/' + ','.join(actor_movies)})
			print('Collection updated')

if __name__  == '__main__':
	print('Keeping the collection updated...')
	try:
		listener = plex.startAlertListener(callback=process)
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		listener.stop()
