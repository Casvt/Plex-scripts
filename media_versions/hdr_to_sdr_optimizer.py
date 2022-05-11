#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Optimize HDR media, found in the libraries given, when it isn't already available in SDR
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

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def _check_media_hdr(ssn, plex, media_ratingkey: str):
	media_info = ssn.get(f'{base_url}/library/metadata/{media_ratingkey}').json()['MediaContainer']['Metadata'][0]
	for media in media_info['Media']:
		if 'title' in media and media['title'].startswith('Optimized for '):
			break
	else:
		plex.fetchItem(int(media_ratingkey)).optimize(locationID=-1, targetTagID=2, deviceProfile='Universal TV')
		return 'Converting'

	return 'Not-Converting'

def hdr_to_sdr_optimizer(ssn, plex, library_name: str, movie_name: list=[], series_name: str=None, season_number: int=None, episode_number: int=None, limit: int=None):
	result_json = []
	counter = 0

	#check for illegal arg parsing
	if season_number != None and series_name == None:
		#season number given but no series name
		return '"season_number" is set but not "series_name"'
	if episode_number != None and (season_number == None or series_name == None):
		#episode number given but no season number or no series name
		return '"episode_number" is set but not "season_number" or "series_name"'

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] != library_name: continue

		#this library is targeted
		print(lib['title'])
		if lib['type'] == 'movie':
			#library is a movie lib; loop through every HDR movie
			lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'hdr': '1'}).json()['MediaContainer']
			if not 'Metadata' in lib_output:
				#no hdr media in the library
				break
			for movie in lib_output['Metadata']:
				if limit != None and counter == limit:
					print('Limit reached')
					return result_json

				if movie_name and not movie['title'] in movie_name:
					#a specific movie is targeted and this one is not it, so skip
					continue

				print(f'	{movie["title"]}')
				counter += 1
				result = _check_media_hdr(ssn, plex, movie['ratingKey'])
				if result == 'Converting':
					print('		Optimizing')
				result_json.append(movie['ratingKey'])

				if movie_name:
					#the targeted movie was found and processed so exit loop
					break

		elif lib['type'] == 'show':
			#library is show lib; loop through every HDR episode
			lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'episode.hdr': '1', 'type': '4'}).json()['MediaContainer']
			if not 'Metadata' in lib_output:
				#no hdr media in the library
				break
			for episode in lib_output['Metadata']:
				if limit != None and counter == limit:
					print('Limit reached')
					return result_json

				if series_name != None and episode['grandparentTitle'] != series_name:
					#a specific show is targeted and this one is not it, so skip
					continue

				if season_number != None and episode['parentIndex'] != season_number:
					#a specific season is targeted and this one is not it, so skip
					continue

				if episode_number != None and episode['index'] != episode_number:
					#a specific episode is targeted and this one is not it, so skip
					continue

				print(f'	{episode["grandparentTitle"]}	- S{episode["parentIndex"]}E{episode["index"]}	- {episode["title"]}')
				counter += 1
				result = _check_media_hdr(ssn, plex, episode['ratingKey'])
				if result == 'Converting':
					print('		Optimizing')
				result_json.append(episode['ratingKey'])

				if episode_number != None:
					#the targeted episode was found and processed so exit loop
					break
			else:
				if episode_number != None:
					#the targeted episode was not found
					return 'Episode not found'

		else:
			return 'Library not supported'
		#the targeted library was found and processed so exit loop
		break
	else:
		#the targeted library was not found
		return 'Library not found'

	return result_json

if __name__ == '__main__':
	import requests, argparse
	from plexapi.server import PlexServer

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})
	plex = PlexServer(base_url, plex_api_token)

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Optimize HDR media, found in the libraries given, when it isn't already available in SDR")
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target library", required=True)
	parser.add_argument('-m', '--MovieName', type=str, help="Target a specific movie inside a movie library based on it's name (only accepted when -l is a movie library); allowed to give argument multiple times", action='append', default=[])
	parser.add_argument('-s', '--SeriesName', type=str, help="Target a specific series inside a show library based on it's name (only accepted when -l is a show library)")
	parser.add_argument('-S', '--SeasonNumber', type=int, help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given) (specials is 0)")
	parser.add_argument('-e', '--EpisodeNumber', type=int, help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given)")
	parser.add_argument('-L', '--Limit', type=int, help="Maximum amount of media that the script is allowed to send to the queue")

	args = parser.parse_args()
	#call function and process result
	response = hdr_to_sdr_optimizer(ssn=ssn, plex=plex, library_name=args.LibraryName, movie_name=args.MovieName, series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber, limit=args.Limit)
	if not isinstance(response, list):
		if response == '"season_number" is set but not "series_name"':
			parser.error('-S/--SeasonNumber given but not -s/--SeriesName given')

		elif response == '"episode_number" is set but not "season_number" or "series_name"':
			parser.error('-e/--EpisodeNumber given but -S/--SeasonNumber or -s/--SeriesName not given')

		else:
			parser.error(response)
