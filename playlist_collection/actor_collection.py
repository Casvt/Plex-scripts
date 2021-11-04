#!/usr/bin/python3

#The use case of this script is the following:
#	Have a collection containing all the movies of the x first actors (and optionally of the movie director) of the last viewed movie
#	The collection will be put in the library from where the source movie originated
#REQUIREMENTS (pip3 install ...):
#	PlexAPI
#	websocket
#	requests

plex_ip = ''
plex_port = ''
plex_api_token = ''
collection_name = 'Actor Collection'

import re

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', plex_ip):
	print("Error: " + plex_ip + " is not a valid ip")
	exit(1)

if not re.search('^\d{1,5}$', plex_port):
	print("Error: " + plex_port + " is not a valid port")
	exit(1)

if not re.search('^[\w\d_-~]{19,21}$', plex_api_token):
	print("Error: " + plex_api_token + " is not a valid api token")
	exit(1)

import requests
import sys, getopt
import time
from plexapi.server import PlexServer

arguments, values = getopt.getopt(sys.argv[1:], 'DA:', ['MovieDirector', 'Actors='])
movie_director = False
actor_count = ''
for argument, value in arguments:
	if argument in ('-D', '--MovieDirector'):
		movie_director = True
	if argument in ('-A', '--Actors'):
		if re.search('^\d+$', value) and int(value) > 0:
			actor_count = int(value)
		else:
			print('Error: value given for Actors is not a number or isn\'t higher than 0')
			exit(1)

if not actor_count:
	print('Error: Arguments were not all given')
	print('Required: -A/--Actors [number]\n		How many of the movie actors should be looked at to take the movies from to include them in the collection')
	print('Optional: -D/--MovieDirector\n		No value needed; Also include all the movies of the director in the collection')
	exit(1)

baseurl = 'http://' + plex_ip + ':' + str(plex_port)
plex = PlexServer(baseurl, plex_api_token)
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})

def process(data):
	if data['PlaySessionStateNotification'][0]['state'] == 'stopped':
		media_output = ssn.get(baseurl + '/library/metadata/' + str(data['PlaySessionStateNotification'][0]['ratingKey'])).json()
		if media_output['MediaContainer']['Metadata'][0]['type'] == 'movie':
			actors = []
			actor_movies = []
			for actor in media_output['MediaContainer']['Metadata'][0]['Role']:
				if len(actors) == actor_count:
					break
				actors.append(actor['id'])
			for actor in actors:
				for actor_movie in ssn.get(baseurl + '/library/sections/' + str(media_output['MediaContainer']['Metadata'][0]['librarySectionID']) + '/all', params={'type': '1', 'actor': actor}).json()['MediaContainer']['Metadata']:
					if not actor_movie['ratingKey'] in actor_movies:
						actor_movies.append(actor_movie['ratingKey'])
			if movie_director:
				for director_movie in ssn.get(baseurl + '/library/sections/' + str(media_output['MediaContainer']['Metadata'][0]['librarySectionID']) + '/all', params={'type': '1', 'director': media_output['MediaContainer']['Metadata'][0]['Director'][0]['id']}).json()['MediaContainer']['Metadata']:
					if not director_movie['ratingKey'] in actor_movies:
						actor_movies.append(director_movie['ratingKey'])
			col_id = ''
			for collection in ssn.get(baseurl + '/library/sections/' + str(media_output['MediaContainer']['Metadata'][0]['librarySectionID']) + '/collections').json()['MediaContainer']['Metadata']:
				if collection['title'] == collection_name:
					col_id = collection['ratingKey']
			machine_id = ssn.get(baseurl + '/').json()['MediaContainer']['machineIdentifier']
			if col_id:
				ssn.delete(baseurl + '/library/collections/' + col_id)
			ssn.post(baseurl + '/library/collections', params={'type': '1', 'title': collection_name, 'smart': '0', 'sectionId': str(media_output['MediaContainer']['Metadata'][0]['librarySectionID']), 'uri': 'server://' + machine_id + '/com.plexapp.plugins.library/library/metadata/' + ','.join(actor_movies)})
			print('Collection updated')

if __name__  == '__main__':
	try:
		listener = plex.startAlertListener(callback=process)
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		listener.stop()
