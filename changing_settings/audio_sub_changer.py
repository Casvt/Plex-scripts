#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Change the audio/subtitle track, based on target language, for an episode, season, series, movie or entire movie/show library
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	You can find examples of the usage below.
Examples:
	--Type audio --Language fr --LibraryName Tv-series
		Try to set the audio for all episodes of all series in the 'Tv-series' library to one with the language French
	--Type subtitle --Language en --LibraryName Tv-series --Series 'Initial D' --SeasonNumber 5
		Try to set the subtitle for season 5 of the series Initial D in the 'Tv-series' library to one with the language English
	--Type subtitle --Language en --LibraryName Films --Movie '2 Fast 2 Furious' --Movie 'The Fast and The Furious'
		Try to set the subtitle for the movies '2 Fast 2 Furious' and 'The Fast and The Furious' inside the 'Films' library to one with the language English
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from re import findall as re_findall

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

langs = ['aa', 'ab', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'br', 'bs', 'ca', 'ce', 'ch', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv', 'dz', 'ee', 'el', 'en', 'en-US', 'en-GB', 'en-AU', 'eo', 'es', 'et', 'eu', 'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz', 'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky', 'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my', 'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps', 'pt', 'qu', 'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty', 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo', 'wa', 'wo', 'xh', 'yi', 'yo', 'za', 'zh', 'zu']

def _set_track(ssn, user_tokens: list, rating_key: str, type: int, language: str):
	#only keep the users that have access to the media and also get media output
	for token in user_tokens:
		r = ssn.get(f'{base_url}/library/metadata/{rating_key}', params={'X-Plex-Token': token}).json()['MediaContainer']
		if 'Metadata' in r:
			media_output = r['Metadata'][0]
		else:
			user_tokens.pop(token)

	if user_tokens:
		for media in media_output['Media']:
			for part in media['Part']:
				#check if media doesn't already have correct stream selected
				for stream in part['Stream']:
					if not stream['streamType'] == type: continue
					if 'languageTag' in stream and stream['languageTag'] == language and 'selected' in stream:
						#media already has correct stream selected
						break
				else:
					#selected stream does not match so find matching one and if found select it
					for stream in part['Stream']:
						if not stream['streamType'] == type: continue
						if 'languageTag' in stream and stream['languageTag'] == language and not 'selected' in stream:
							#found matching stream so select it
							for token in user_tokens:
								if type == 2:
									#set audio stream
									ssn.put(f'{base_url}/library/parts/{part["id"]}', params={'audioStreamID': stream['id'], 'allParts': 0, 'X-Plex-Token': token})
								elif type == 3:
									#set subtitle stream
									ssn.put(f'{base_url}/library/parts/{part["id"]}', params={'subtitleStreamID': stream['id'], 'allParts': 0, 'X-Plex-Token': token})
							break
	return

def audio_sub_changer(ssn, type: str, language: str, library_name: str, movie_name: list=[], series_name: str=None, season_number: int=None, episode_number: int=None, users: list=[]):
	result_json = []

	#check for illegal arg parsing
	if not language in langs: return 'Unknown language'
	if not type in ('audio','subtitle'):
		#type is not set to audio or subtitle
		return 'Unknown type'
	if season_number != None and series_name == None:
		#season number given but no series name
		return '"season_number" is set but not "series_name"'
	if episode_number != None and (season_number == None or series_name == None):
		#episode number given but no season number or no series name
		return '"episode_number" is set but not "season_number" or "series_name"'
	type = 2 if type == 'audio' else 3

	#setup users
	user_tokens = []
	if not users:
		#just add the user self
		user_tokens = [plex_api_token]
	else:
		#add the tokens of multiple users
		machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
		shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers', headers={}).text

		#add user self if requested
		if '@me' in users or '@all' in users:
			user_tokens = [plex_api_token]

		#get data about every user (username at beginning and token at end)
		user_data = re_findall(r'(?<=username=").*?accessToken="\w+?(?=")', shared_users)
		for user in user_data:
			username = user.split('"')[0]
			if not '@all' in users and not username in users:
				continue
			token = user.split('"')[-1]
			user_tokens.append(token)

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] != library_name: continue

		#this library is targeted
		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer']['Metadata']
		if lib['type'] == 'movie':
			#library is a movie lib; loop through every movie
			for movie in lib_output:
				if movie_name and not movie['title'] in movie_name:
					#a specific movie is targeted and this one is not it, so skip
					continue

				print(f'	{movie["title"]}')
				_set_track(ssn=ssn, user_tokens=user_tokens, rating_key=movie['ratingKey'], type=type, language=language)
				result_json.append(movie['ratingKey'])

		elif lib['type'] == 'show':
			#library is show lib; loop through every show
			for show in lib_output:
				if series_name != None and show['title'] != series_name:
					#a specific show is targeted and this one is not it, so skip
					continue

				print(f'	{show["title"]}')
				show_output = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']
				#loop through episodes of show to check if targeted season exists
				if season_number != None:
					for episode in show_output:
						if episode['parentIndex'] == season_number:
							break
					else:
						return 'Season not found'
				#loop through episodes of show
				for episode in show_output:
					if season_number != None and episode['parentIndex'] != season_number:
						#a specific season is targeted and this one is not it; so skip
						continue

					if episode_number != None and episode['index'] != episode_number:
						#this season is targeted but this episode is not; so skip
						continue

					print(f'		S{episode["parentIndex"]}E{episode["index"]}	- {episode["title"]}')
					_set_track(ssn=ssn, user_tokens=user_tokens, rating_key=episode['ratingKey'], type=type, language=language)
					result_json.append(episode['ratingKey'])

					if episode_number != None:
						#the targeted episode was found and processed so exit loop
						break
				else:
					if episode_number != None:
						#the targeted episode was not found
						return 'Episode not found'

				if series_name != None:
					#the targeted series was found and processed so exit loop
					break
			else:
				if series_name != None:
					#the targeted series was not found
					return 'Series not found'
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

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Change the audio/subtitle track, based on target language, for an episode, season, series, movie or entire movie/show library")
	parser.add_argument('-t', '--Type', choices=['audio','subtitle'], help="Give the type of stream to change", required=True)
	parser.add_argument('-L', '--Language', type=str, help="ISO-639-1 (2 lowercase letters) language code (e.g. 'en') to try to set the stream to", required=True)
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target library", required=True)
	parser.add_argument('-m', '--MovieName', type=str, help="Target a specific movie inside a movie library based on it's name (only accepted when -l is a movie library); allowed to give argument multiple times", action='append', default=[])
	parser.add_argument('-s', '--SeriesName', type=str, help="Target a specific series inside a show library based on it's name (only accepted when -l is a show library)")
	parser.add_argument('-S', '--SeasonNumber', type=int, help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given) (specials is 0)")
	parser.add_argument('-e', '--EpisodeNumber', type=int, help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given)")
	parser.add_argument('-u', '--User', type=str, help="Select the user(s) to apply this script to; Give username, '@me' for yourself or '@all' for everyone; allowed to give argument multiple times", action='append', default=[])

	args = parser.parse_args()
	#call function and process result
	response = audio_sub_changer(ssn=ssn, type=args.Type, language=args.Language, library_name=args.LibraryName, movie_name=args.MovieName, series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber, users=args.User)
	if not isinstance(response, list):
		if response == 'Unknown language':
			parser.error('-l/--Language requires a valid language code')

		elif response == '"season_number" is set but not "series_name"':
			parser.error('-S/--SeasonNumber given but not -s/--SeriesName given')

		elif response == '"episode_number" is set but not "season_number" or "series_name"':
			parser.error('-e/--EpisodeNumber given but -S/--SeasonNumber or -s/--SeriesName not given')

		else:
			parser.error(response)
