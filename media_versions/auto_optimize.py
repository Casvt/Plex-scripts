#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Automatically optimize media, found in the libraries given, when it isn't already available in that profile
Requirements (python3 -m pip install [requirement]):
	requests
	PlexAPI
Setup:
	Fill the variables below firstly, then run the script.
	Check the help page (python3 auto_optimize.py --help) to see how to use the script with it's arguments.
	When the script is run with it's arguments, it will show you what media it has processed and will let you know if it has added it to the queue
To-Do:
	1. Don't add media to the optimize-queue when it's already there
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from plexapi.server import PlexServer
import requests, argparse

baseurl = f'http://{plex_ip}:{plex_port}'
plex = Plex.Server(baseurl, plex_api_token)
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})

def optimize_check(movie):
	for media in movie['Media']:
		for part in media['Part']:
			if args.Profile in ('Mobile','TV'):
				if f'/Optimized for {args.Profile}/' in part['file']: return 'Optimized'
			elif args.Profile == 'Original Quality':
				if f'/{args.Profile}/' in part['file']: return 'Optimized'
	return 'Not-Optimized'

#process arguments
parser = argparse.ArgumentParser(description="Automatically optimize media when it isn't already available in that profile")
parser.add_argument('-L', '--Library', help="Give the name of the library to scan; allowed to give argument multiple times to process multiple libraries", required=True, type=str, action='append')
parser.add_argument('-P', '--Profile', help="Select the profile", choices=['Mobile','TV','Original Quality'], type=str, required=True)
parser.add_argument('-l', '--Limit', help="Maximum amount of media that the script is allowed to send to the queue", typ=int)
args = parser.parse_args()

#Do not give a value; leave these empty
lib_ids = []
lib_types = {}
counter = 0
for level in ssn.get(baseurl + '/library/sections').json()['MediaContainer']['Directory']:
	#go through every library; if it's in the list, note it's type and key
	if level['title'] in args.Library:
		lib_ids.append(level['key'])
		lib_types[level['key']] = level['type']

for lib in lib_ids:
	#do this for every library
	lib_output = ssn.get(baseurl + '/library/sections/' + lib + '/all').json()
	if lib_types[lib] == 'movie':
		#lib is a movie lib
		for movie in lib_output['MediaContainer']['Metadata']:
			#do this for every movie in the lib
			if args.Limit != None and counter == args.Limit:
				print('Limit reached')
				exit(0)
			print(movie['title'])
			if not optimize_check(movie) == 'Optimized':
				#movie doesn't have an optimized version
				print(f'	Not optimized for {args.Profile}; optimizing')
				counter += 1
				if args.Profile == 'Mobile':
					plex.fetchItem(movie['ratingKey']).optimize(locationID=-1, targetTagID=1)
				elif args.Profile == 'TV':
					plex.fetchItem(movie['ratingKey']).optimize(locationID=-1, targetTagID=2)
				elif args.Profile == 'Original Quality':
					plex.fetchItem(movie['ratingKey']).optimize(locationID=-1, targetTagID=3)

	elif lib_types[lib] == 'show':
		#lib is a show lib
		for show in lib_output['MediaContainer']['Metadata']:
			#do this for every show in the lib
			print(show['title'])
			for episode in ssn.get(baseurl + '/library/metadata/' + show['ratingKey'] + '/allLeaves').json()['MediaContainer']['Metadata']:
				#do this for every episode of the show
				if args.Limit != None and counter == args.Limit:
					print('Limit reached')
					exit(0)
				print('	' + show['title'] + ' - S' + str(episode['parentIndex']) + 'E' + str(episode['index']) + ' - ' + episode['title'])
				if not optimize_check(episode) == 'Optimized':
					#episode doesn't have an optimized version
					print(f'	Not optimized for {args.Profile}; optimizing')
					counter += 1
					if args.Profile == 'Mobile':
						plex.fetchItem(episode['ratingKey']).optimize(locationID=-1, targetTagID=1)
					elif args.Profile == 'TV':
						plex.fetchItem(episode['ratingKey']).optimize(locationID=-1, targetTagID=2)
					elif args.Profile == 'Original Quality':
						plex.fetchItem(episode['ratingKey']).optimize(locationID=-1, targetTagID=3)

	else: print('Invalid library; skipping')
