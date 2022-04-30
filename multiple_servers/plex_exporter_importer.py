#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Export plex metadata to a file that then can be imported later
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script.
Note:
	Changing the value of "Original Date" always results in value of 1970-01-01
	This is a bug that will be fixed in plex server version 1.26.1
To-Do:
	Collections
	Music lib
	Playlists
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import os, json, re

# Environmental Variables
plex_ip = os.getenv('plex_ip', plex_ip)
plex_port = os.getenv('plex_port', plex_port)
plex_api_token = os.getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def _export_media(type: str, data: dict, ssn, download_poster: bool, export_watched: bool):
	result_json = {}
	#extract different data based on the type
	keys = []
	if type == 'movie':
		keys = [
			'title', 'titleSort', 'originalTitle',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio', 'tagline', 'summary',
			'Genre', 'Writer', 'Director', 'Collection'
		]
		root_file = os.path.splitext(data['Media'][0]['Part'][0]['file'])[0]

	elif type == 'show':
		keys = [
			'title', 'titleSort', 'originalTitle',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio', 'tagline', 'summary',
			'Genre', 'Collection'
		]
		root_file = os.path.join(data['Location'][0]['path'], 'series')

	elif type == 'season':
		keys = [
			'title', 'summary'
		]
		season_output = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		root_file = os.path.join(os.path.dirname(season_output[0]['Media'][0]['Part'][0]['file']), 'season')

	elif type == 'episode':
		keys = [
			'title', 'titleSort',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'summary',
			'Writer', 'Director'
		]
		root_file = os.path.splitext(data['Media'][0]['Part'][0]['file'])[0]

	else:
		#unknown type of source
		return 'Unknown source type when trying to extract data (internal error)'

	rating_key = data['ratingKey']
	media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}').json()['MediaContainer']['Metadata'][0]

	#build file paths
	file_data = f'{root_file}_metadata.json'
	if download_poster == True:
		thumb_url = media_info['thumb']
		art_url = media_info['art']
		file_thumb = f'{root_file}_thumb.jpg'
		file_art = f'{root_file}_art.jpg'

	#extract keys
	for key in keys:
		result_json[key] = media_info[key] if key in media_info.keys() else None

	#when original title is not in api output, it is the same as title (stupid decision of plex)
	if 'titleSort' in result_json.keys() and result_json['titleSort'] == None:
		result_json['titleSort'] = result_json['title']

	#extract special metadata
	if export_watched == True:
		#get watched status of admin
		if 'viewOffset' in media_info.keys():
			result_json[f'_watched_admin'] = media_info['viewOffset']
		elif 'viewCount' in media_info.keys():
			result_json[f'_watched_admin'] = True
		else:
			result_json[f'_watched_admin'] = False

		#get watched status of all other users
		machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
		shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers', headers={}).text

		user_ids = re.findall(r'(?<=userID=")\d+(?=")', shared_users)
		user_tokens = re.findall(r'(?<=accessToken=")\w+(?=")', shared_users)
		for user_id, user_token in zip(user_ids, user_tokens):
			user_watched = ssn.get(f'{base_url}/library/metadata/{rating_key}', params={'X-Plex-Token': user_token}).json()['MediaContainer']['Metadata'][0]
			if 'viewOffset' in user_watched.keys():
				result_json[f'_watched_{user_id}'] = user_watched['viewOffset']
			elif 'viewCount' in user_watched.keys():
				result_json[f'_watched_{user_id}'] = True
			else:
				result_json[f'_watched_{user_id}'] = False
	if download_poster == True:
		thumb = ssn.get(f'{base_url}{thumb_url}').content
		art = ssn.get(f'{base_url}{art_url}').content

	#all data is extracted, put them into files

	#put data into file
	json.dump(result_json, open(file_data, 'w+'), indent=4)
	if download_poster == True:
		#put thumb (poster) into file
		with open(file_thumb, 'wb') as f_thumb:
			f_thumb.write(thumb)
		#put art (background; fan-art) into file
		with open(file_art, 'wb') as f_art:
			f_art.write(art)

	return result_json

def _import_media(type: str, data: dict, media_lib_id: str, ssn, import_watched: bool):
	result_json = {}
	#build paths to metadata files
	if type == 'movie':
		root_file = os.path.splitext(data['Media'][0]['Part'][0]['file'])[0]
		media_type = 1

	elif type == 'show':
		root_file = os.path.join(data['Location'][0]['path'], 'series')
		media_type = 2

	elif type == 'season':
		season_output = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		root_file = os.path.join(os.path.dirname(season_output[0]['Media'][0]['Part'][0]['file']), 'season')
		media_type = 3

	elif type == 'episode':
		root_file = os.path.splitext(data['Media'][0]['Part'][0]['file'])[0]
		media_type = 4

	else:
		#unknown type of source
		return 'Unknown source type when trying to import data (internal error)'

	rating_key = data['ratingKey']
	media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}').json()['MediaContainer']['Metadata'][0]
	if import_watched == True:
		machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
		shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers', headers={}).text

	file_data = f'{root_file}_metadata.json'
	file_thumb = f'{root_file}_thumb.jpg'
	file_art = f'{root_file}_art.jpg'

	if os.path.isfile(file_data):
		#metadata file exists for this media
		file_data_json = json.load(open(file_data, 'r'))
		payload = {
			'type': media_type,
			'id': rating_key,
			'thumb.locked': 1,
			'art.locked': 1
		}

		#build the payload that sets all the values
		for option, value in file_data_json.items():
			if option.startswith('_'):
				#special metadata
				if option.startswith('_watched_') and import_watched == True:
					#set the token of the user
					if option == '_watched_admin':
						user_token = plex_api_token
					else:
						user_id = option.split('_')[2]
						user_token = re.search(rf'(?<=userID="{user_id}" accessToken=")\w+(?=")', shared_users)
						if user_token:
							user_token = user_token.group(0)
						else:
							continue

					#set watched status of media for this user
					if value == True:
						#mark media as watched
						ssn.get(f'{base_url}/:/scrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key, 'X-Plex-Token': user_token})
					elif value == False:
						#mark media as not-watched
						ssn.get(f'{base_url}/:/unscrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key, 'X-Plex-Token': user_token})
					elif isinstance(value, int):
						#set media to offset (partially watched; on deck)
						ssn.get(f'{base_url}/:/progress', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key, 'time': value, 'state': 'stopped', 'X-Plex-Token': user_token})

			elif option in ('Genre','Writer','Director','Collection') or isinstance(value, list):
				#list of labels
				if value == None: value = []
				option = option.lower()
				#add tags
				for offset, list_item in enumerate(value):
					payload[f'{option}[{offset}].tag.tag'] = list_item["tag"]
				#remove other tags
				if option.capitalize() in media_info:
					for list_item in media_info[option.capitalize()]:
						if not f'{option}[].tag.tag-' in payload:
							payload[f'{option}[].tag.tag-'] = list_item['tag']
						else:
							payload[f'{option}[].tag.tag-'] += f',{list_item["tag"]}'
				payload[f'{option}.locked'] = 1
			else:
				#normal key-value pair
				value = value or ''
				payload[f'{option}.value'] = value
				payload[f'{option}.locked'] = 1

		#upload to plex
		ssn.put(f'{base_url}/library/sections/{media_lib_id}/all', params=payload)

		result_json = file_data_json

	if os.path.isfile(file_thumb):
		#poster file exists for this media
		with open(file_thumb, 'rb') as f:
			data = f.read()
		ssn.post(f'{base_url}/library/metadata/{rating_key}/posters', data=data)

	if os.path.isfile(file_art):
		#background file exists for this media
		with open(file_art, 'rb') as f:
			data = f.read()
		ssn.post(f'{base_url}/library/metadata/{rating_key}/arts', data=data)

	return result_json

def plex_exporter_importer(type: str, ssn, all: bool, export_posters: bool, export_watched: bool, lib_id: str=None, movie_name: str=None, series_name: str=None, season_number: int=None, episode_number: int=None):
	#returning non-list is for errors

	result_json = []
	#preparation and checks
	if not type in ('import','export'):
		#type is not set to import or export
		return 'Invalid value for "type"'
	if all == True:
		print('Exporting complete plex library')
	if all == True and (lib_id != None or movie_name != None or series_name != None or season_number != None or episode_number != None):
		#all is set to True but a target-specifier is also set
		return 'Both "all" and a target-specifier are set'
	if all == False:
		if lib_id == None:
			#all = False but lib_id is not given
			return 'Library ID not given (lib_id)'
		if season_number != None and series_name == None:
			#season number given but no series name
			return '"season_number" is set but not "series_name"'
		if episode_number != None and (season_number == None or series_name == None):
			#episode number given but no season number or no series name
			return '"episode_number" is set but not "season_number" or "series_name"'

	method = _export_media if type == 'export' else _import_media
	args = {'ssn': ssn}
	if type == 'export':
		args['download_poster'] = export_posters
		args['export_watched'] = export_watched
	else:
		args['import_watched'] = export_watched

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib_id != None and lib['key'] != lib_id:
			#a specific library is targeted and this one is not it, so skip
			continue

		#this library (or something in it) should be exported/imported
		print(lib['title'])
		if type == 'import':
			args['media_lib_id'] = lib['key']
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer']['Metadata']
		if lib['type'] == 'movie':
			#library is movie lib; loop through every movie
			for movie in lib_output:
				if movie_name != None and movie['title'] != movie_name:
					#a specific movie is targeted and this one is not it, so skip
					continue

				print(f'	{movie["title"]}')
				#export/import movie
				result = method(type='movie', data=movie, **args)
				if isinstance(result, str): return result
				if result: result_json.append(result)

		elif lib['type'] == 'show':
			#library is show lib; loop through every show
			for show in lib_output:
				if series_name != None and show['title'] != series_name:
					#a specific show is targeted and this one is not it, so skip
					continue

				print(f'	{show["title"]}')
				show_output = ssn.get(f'{base_url}{show["key"]}').json()
				show_info = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}').json()['MediaContainer']['Metadata'][0]
				#export/import show data
				result = method(type='show', data=show_info, **args)
				if isinstance(result, str): return result
				if result: result_json.append(result)

				#loop through seasons of show; for season exporting
				for season in show_output['MediaContainer']['Metadata']:
					if season_number != None and season['index'] != season_number:
						#a specific season is targeted and this one is not it, so skip
						continue

					#export/import season data
					result = method(type='season', data=season, **args)
					if isinstance(result, str): return result
					if result: result_json.append(result)

					if season_number != None:
						#the targeted season was found and processed so exit loop
						break
				else:
					if season_number != None:
						#the targeted season was not found
						return 'Season not found'

				#loop through episodes of show; for episode exporting
				show_content = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']
				for episode in show_content:
					if season_number != None and episode['parentIndex'] != season_number:
						#a specific season is targeted and this one is not it; so skip
						continue

					if episode_number != None and episode['index'] != episode_number:
						#this season is targeted but this episode is not; so skip
						continue

					print(f'		S{episode["parentIndex"]}E{episode["index"]}	- {episode["title"]}')
					#export/import episode data
					result = method(type='episode', data=episode, **args)
					if isinstance(result, str): return result
					if result: result_json.append(result)

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
			#library not supported
			print('	Library not supported')

		if lib_id != None:
			#the targeted library was found and processed so exit loop
			break
	else:
		if lib_id != None:
			#the targeted library was not found
			return 'Library not found'

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept':'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Export Plex metadata to a file that then can be imported later')
	parser.add_argument('-t','--Type', choices=['import','export'], required=True, type=str, help='Either export metadata or import it into plex')
	parser.add_argument('-p','--NoPosters', action='store_true', help='EXPORT ONLY: Disable exporting media posters and backgrounds')
	parser.add_argument('-w','--NoWatched', action='store_true', help='Disable exporting/importing watched status for every user')

	#args regarding target selection
	parser.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	parser.add_argument('-l','--LibraryName', type=str, help='Target a specific library based on it\'s name (movie and show libraries supported)')
	parser.add_argument('-m','--MovieName', type=str, help='Target a specific movie inside a movie library based on it\'s name (only accepted when -l is a movie library)')
	parser.add_argument('-s','--SeriesName', type=str, help='Target a specific series inside a show library based on it\'s name (only accepted when -l is a show library)')
	parser.add_argument('-S','--SeasonNumber', type=int, help='Target a specific season inside the targeted series based on it\'s number (only accepted when -s is given) (specials is 0)')
	parser.add_argument('-e','--EpisodeNumber', type=int, help='Target a specific episode inside the targeted season based on it\'s number (only accepted when -S is given)')

	args = parser.parse_args()
	#get general info about targets, check for illegal arg parsing and call functions
	if args.NoPosters == True and args.Type == 'import':
		#--NoPosters was given but the type is 'import' (--NoPosters is only for 'export')
		parser.error('-p/--NoPosters was given but -t/--Type was set to \'import\'')

	if args.All == True:
		#user selected --All
		plex_exporter_importer(type=args.Type, ssn=ssn, all=True, export_posters=False if args.NoPosters == True else True, export_watched=False if args.NoWatched == True else True)
	else:
		#user is more specific
		sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
		for lib in sections:
			if lib['title'] == args.LibraryName:
				#library found
				response = plex_exporter_importer(type=args.Type, ssn=ssn, all=False, lib_id=lib['key'], movie_name=args.MovieName, series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber, export_posters=False if args.NoPosters == True else True, export_watched=False if args.NoWatched == True else True)
				if not isinstance(response, list):
					if response == 'Library ID not given (lib_id)':
						parser.error('Neither -a/--All or -l/--LibraryName given')

					elif response == 'Both "all" and a target-specifier are set':
						parser.error('-a/--All was given but also an other more specific target specifier')

					elif response == '"season_number" is set but not "series_name"':
						parser.error('-S/--SeasonNumber given but not -s/--SeriesName given')

					elif response == '"episode_number" is set but not "season_number" or "series_name"':
						parser.error('-e/--EpisodeNumber given but -S/--SeasonNumber or -s/--SeriesName not given')

					else:
						parser.error(response)
