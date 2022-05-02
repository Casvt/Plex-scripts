#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Automatically optimize media, found in the libraries given, when it isn't already available in that profile
Requirements (python3 -m pip install [requirement]):
	requests
	PlexAPI
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
To-Do:
	1. Don't add media to the optimize-queue when it's already there
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from plexapi.server import PlexServer

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"
plex = PlexServer(base_url, plex_api_token)

def _optimize_check(media_info, profile):
	for media in media_info['Media']:
		for part in media['Part']:
			if profile in ('Mobile','TV'):
				if f'/Optimized for {profile}/' in part['file']: return True
			elif profile == 'Original Quality':
				if f'/{profile}/' in part['file']: return True
	return False

def auto_optimize(ssn, profile: str, library_names: list, limit: int=None):
	counter = 0

	#check for illegal arg parsing
	if not profile in ('Mobile','TV','Original Quality'):
		#profile is not set to a valid preset
		return 'Unknown profile'

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if not lib['title'] in library_names: continue

		#this library is targeted
		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer']['Metadata']
		if lib['type'] == 'movie':
			#library is a movie lib; loop through every movie
			for movie in lib_output:
				if limit != None and counter == limit:
					print('Limit reached')
					return

				print(f'	{movie["title"]}')
				if _optimize_check(movie, profile) == False:
					#movie doesn't have an optimized version
					print(f'		Not optimized for {profile}; optimizing')
					counter += 1
					if profile == 'Mobile':
						plex.fetchItem(movie['ratingKey']).optimize(locationID=-1, targetTagID=1)
					elif profile == 'TV':
						plex.fetchItem(movie['ratingKey']).optimize(locationID=-1, targetTagID=2)
					elif profile == 'Original Quality':
						plex.fetchItem(movie['ratingKey']).optimize(locationID=-1, targetTagID=3)

		elif lib['type'] == 'show':
			#library is a show lib; loop through every show
			for show in lib_output:
				print(f'	{show["title"]}')
				show_output = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']
				#loop through episodes of show
				for episode in show_output:
					if limit != None and counter == limit:
						print('Limit reached')
						return

					print(f'		S{episode["parentIndex"]}E{episode["index"]}	- {episode["title"]}')
					if _optimize_check(episode, profile) == False:
						#episode doesn't have an optimized version
						print(f'			Not optimized for {profile}; optimizing')
						counter += 1
						if profile == 'Mobile':
							plex.fetchItem(episode['ratingKey']).optimize(locationID=-1, targetTagID=1)
						elif profile == 'TV':
							plex.fetchItem(episode['ratingKey']).optimize(locationID=-1, targetTagID=2)
						elif profile == 'Original Quality':
							plex.fetchItem(episode['ratingKey']).optimize(locationID=-1, targetTagID=3)
		else:
			return 'Library not supported'

	return

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Automatically optimize media when it isn't already available in that profile")
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target library; allowed to give argument multiple times", action='append', required=True)
	parser.add_argument('-P', '--Profile', type=str, choices=['Mobile','TV','Original Quality'], help="The optimization profile", required=True)
	parser.add_argument('-L', '--Limit', type=int, help="Maximum amount of media that the script is allowed to send to the queue")

	args = parser.parse_args()
	#call function and process result
	response = auto_optimize(ssn=ssn, profile=args.Profile, library_names=args.LibraryName, limit=args.Limit)
	if response != None:
		parser.error(response)
