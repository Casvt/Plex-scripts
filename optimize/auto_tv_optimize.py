#!/usr/bin/python3

#The use case of this script is the following:
#	Check every library given inside the list and if one of the movies/episodes isn't 'optimized for tv' by plex,
#	it will initiate the 'optimize for tv' for the movie/episode

plex_ip = ''
plex_port = ''
plex_api_token = ''

#Give the names of the library to scan (e.g. library_names = ['Films', 'Tv-series'])
library_names = []

from plexapi.server import PlexServer
import requests
import json
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

lib_ids = []
lib_types = {}
baseurl = 'http://' + plex_ip + ':' + plex_port
plex = PlexServer(baseurl, plex_api_token)
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})

def optimize_check(movie):
	for media in movie['Media']:
		for part in media['Part']:
			if re.search('/Optimized for TV/', part['file']): return('Optimized')


for level in json.loads(ssn.get(baseurl + '/library/sections').text)['MediaContainer']['Directory']:
	#go through every library; if it's in the list, note it's type and key
	if level['title'] in library_names:
		lib_ids.append(level['key'])
		lib_types[level['key']] = level['type']

for lib in lib_ids:
	#do this for every library
	lib_output = json.loads(ssn.get(baseurl + '/library/sections/' + lib + '/all').text)
	if lib_types[lib] == 'movie':
		#lib is a movie lib
		for movie in lib_output['MediaContainer']['Metadata']:
			#do this for every movie in the lib
			print(movie['title'])
			if not optimize_check(movie) == 'Optimized':
				#movie doesn't have an optimized version
				print('	Not optimized for TV')
				plex.fetchItem(movie['ratingKey']).optimize(locationID=-1, targetTagID=2, deviceProfile='Universal TV')
			else: print('	Optimized for TV')

	elif lib_types[lib] == 'show':
		#lib is a show lib
		for show in lib_output['MediaContainer']['Metadata']:
			#do this for every show in the lib
			print(show['title'])
			for episode in json.loads(ssn.get(baseurl + '/library/metadata/' + show['ratingKey'] + '/allLeaves').text)['MediaContainer']['Metadata']:
				#do this for every episode of the show
				print('	' + show['title'] + ' - S' + str(episode['parentIndex']) + 'E' + str(episode['index']) + ' - ' + episode['title'])
				if not optimize_check(episode) == 'Optimized':
					#episode doesn't have an optimized version
					print('		Not optimized for TV')
					plex.fetchItem(episode['ratingKey']).optimize(locationID=-1, targetTagID=2, deviceProfile='Universal TV')
				else: print('		Optimized for TV')

	else: print('Invalid library; skipping')
