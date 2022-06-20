#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Export plex metadata to a file that can then be imported back later
Requirements (python3 -m pip install [requirement]):
	requests
	aiohttp
Setup:
	Fill the variables below firstly, then run the script.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

#ADVANCED SETTINGS
#Hardcode the folder where the plex database is in
#Leave empty unless really needed
database_folder = ''

from os import path, getenv
from json import dump, load
from re import findall
from asyncio import run, gather
from aiohttp import ClientSession

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"
database_folder = getenv('database_folder', database_folder)

async def _download_posters(session, url, poster_queue):
	async with session.get(url, params={'X-Plex-Token': plex_api_token}) as r:
		with open(poster_queue[url], 'wb') as f:
			f.write(await r.read())

async def _export_posters(poster_queue):
	async with ClientSession() as session:
		tasks = [_download_posters(session, u, poster_queue) for u in poster_queue.keys()]
		await gather(*tasks)

def _export_media(
		type: str, data: dict, ssn, user_data: tuple, poster_queue: dict, settings_queue: dict, reset_queue: dict, watched_map: dict,
		export_poster: bool, export_art: bool, export_episode_poster: bool, export_episode_art: bool, export_watched: bool, export_metadata: bool, export_intro_markers: bool
	):
	result_json = {}
	user_ids, user_tokens = user_data
	#extract different data based on the type
	if type == 'movie':
		keys = (
			'title', 'titleSort', 'originalTitle',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio', 'tagline', 'summary',
			'Genre', 'Writer', 'Director', 'Collection'
		)
		root_file = path.splitext(data['Media'][0]['Part'][0]['file'])[0]

	elif type == 'show':
		keys = (
			'title', 'titleSort', 'originalTitle',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio', 'tagline', 'summary',
			'Genre', 'Collection'
		)
		root_file = path.join(data['Location'][0]['path'], 'series')

	elif type == 'season':
		keys = (
			'title', 'summary'
		)
		season_output = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		root_file = path.join(path.dirname(season_output[0]['Media'][0]['Part'][0]['file']), 'season')

	elif type == 'episode':
		keys = (
			'title', 'titleSort',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'summary',
			'Writer', 'Director'
		)
		root_file = path.splitext(data['Media'][0]['Part'][0]['file'])[0]

	elif type == 'artist':
		keys = (
			'title', 'titleSort', 'summary',
			'Genre', 'Style', 'Mood', 'Country', 'Collection', 'Similar'
		)
		root_file = path.join(data['Location'][0]['path'], 'artist')

	elif type == 'album':
		keys = (
			'title', 'titleSort',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio','summary',
			'Genre', 'Style', 'Mood', 'Collection'
		)
		album_output = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		root_file = path.join(path.dirname(album_output[0]['Media'][0]['Part'][0]['file']), 'album')

	elif type == 'track':
		keys = (
			'title', 'originalTitle',
			'contentRating', 'userRating', 'index', 'parentIndex',
			'Mood'
		)
		root_file = path.splitext(data['Media'][0]['Part'][0]['file'])[0]

	else:
		#unknown type of source
		return 'Unknown source type when trying to extract data (internal error)'

	rating_key = data['ratingKey']
	media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}', params={'includeMarkers': '1'})
	if media_info.status_code != 200: return result_json
	media_info = media_info.json()['MediaContainer']['Metadata'][0]

	#build file paths and extract poster/art
	file_data = f'{root_file}_metadata.json'
	thumb_url = media_info.get('thumb', None)
	art_url = media_info.get('art', None)
	if thumb_url != None and ((not type in ('episode','track') and export_poster == True) or (type == 'episode' and export_episode_poster == True)):
		file_thumb = f'{root_file}_thumb.jpg'
		poster_queue[f'{base_url}{thumb_url}'] = file_thumb
	if art_url != None and ((not type in ('episode','track') and export_art == True) or (type == 'episode' and export_episode_art == True)):
		file_art = f'{root_file}_art.jpg'
		poster_queue[f'{base_url}{art_url}'] = file_art

	#extract keys
	if export_metadata == True:
		for key in keys:
			result_json[key] = media_info.get(key, None)

		if type != 'track':
			#when original title is not in api output, it is the same as title (stupid decision of plex)
			result_json['titleSort'] = media_info.get('titleSort', result_json['title'])

	#extract special metadata
	if export_watched == True and type in ('movie','episode'):
		#get watched status of admin
		result_json['_watched_admin'] = media_info.get('viewOffset', 'viewCount' in media_info)

		#get watched status of all other users
		for user_id, user_token in zip(user_ids, user_tokens):
			result_json[f'_watched_{user_id}'] = watched_map[user_token].get(rating_key)

	if export_intro_markers == True and type == 'episode':
		for marker in media_info.get('Marker',[]):
			if marker['type'] == 'intro':
				#intro marker found
				result_json['_intro_marker'] = {
					'intro_start': marker['startTimeOffset'],
					'intro_end': marker['endTimeOffset']
				}
				break

	#put data into file
	if export_metadata == True or (export_watched == True and type in ('movie','episode')) or (export_intro_markers == True and type == 'episode'):
		dump(result_json, open(file_data, 'w+'), indent=4)

	return result_json, poster_queue, settings_queue, reset_queue

async def _import_queue(poster_queue, settings_queue):
	async with ClientSession() as session:
		tasks = [session.post(u, data=d, params={'X-Plex-Token': plex_api_token}) for u, d in poster_queue.items()]
		tasks += [session.put(x[0], params=x[1]) for x in settings_queue]
		await gather(*tasks)

def _import_media(
		type: str, data: dict, media_lib_id: str, ssn, user_data: tuple, poster_queue: dict, settings_queue: dict, reset_queue: dict,
		import_poster: bool, import_art: bool, import_episode_poster: bool, import_episode_art: bool, import_watched: bool, import_metadata: bool, import_intro_markers: bool
	):
	result_json = {}
	user_ids, user_tokens = user_data
	#build paths to metadata files
	if type == 'movie':
		root_file = path.splitext(data['Media'][0]['Part'][0]['file'])[0]
		media_type = 1

	elif type == 'show':
		root_file = path.join(data['Location'][0]['path'], 'series')
		media_type = 2

	elif type == 'season':
		season_output = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		root_file = path.join(path.dirname(season_output[0]['Media'][0]['Part'][0]['file']), 'season')
		media_type = 3

	elif type == 'episode':
		root_file = path.splitext(data['Media'][0]['Part'][0]['file'])[0]
		media_type = 4

	elif type == 'artist':
		root_file = path.join(data['Location'][0]['path'], 'artist')
		media_type = 8

	elif type == 'album':
		album_output = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		root_file = path.join(path.dirname(album_output[0]['Media'][0]['Part'][0]['file']), 'album')
		media_type = 9

	elif type == 'track':
		root_file = path.splitext(data['Media'][0]['Part'][0]['file'])[0]
		media_type = 10

	else:
		#unknown type of source
		return 'Unknown source type when trying to import data (internal error)'

	rating_key = data['ratingKey']
	if import_metadata == True or import_intro_markers == True:
		media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}', params={'includeMarkers': '1'})
		if media_info.status_code != 200: return result_json
		media_info = media_info.json()['MediaContainer']['Metadata'][0]

	file_data = f'{root_file}_metadata.json'
	file_thumb = f'{root_file}_thumb.jpg'
	file_art = f'{root_file}_art.jpg'

	if path.isfile(file_data) and True in (import_metadata, import_watched, import_intro_markers):
		#metadata file exists for this media
		file_data_json = load(open(file_data, 'r'))
		if import_metadata == True:
			payload = {
				'type': media_type,
				'id': rating_key,
				'thumb.locked': 1,
				'art.locked': 1,
				'X-Plex-Token': plex_api_token
			}
			if type == 'album':
				payload['artist.id.value'] = data['parentRatingKey']

		if '_intro_marker' in file_data_json:
			from sqlite3 import connect
			from datetime import datetime
			from os.path import join, isfile

			#get location to database file
			if database_folder == '':
				db_folder = [s['value'] for s in ssn.get(f'{base_url}/:/prefs').json()['MediaContainer']['Setting'] if s['id'] == 'ButlerDatabaseBackupPath'][0]
			db_file = join(db_folder, 'com.plexapp.plugins.library.db')
			if not isfile(db_file):
				return 'Intro Marker importing is requested but script is not run on target plex server, or value of database_folder is invalid'

			#setup db connection
			db = connect(db_file)
			cursor = db.cursor()

		#build the payload that sets all the values
		for option, value in file_data_json.items():
			if option.startswith('_'):
				#special metadata
				if import_watched == True and option.startswith('_watched_'):
					#set the token of the user
					if option == '_watched_admin':
						user_token = plex_api_token
					else:
						user_id = option.split('_')[-1]
						user_token = user_tokens[user_ids.index(user_id)]

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

				elif import_intro_markers == True and option == '_intro_marker':
					#check if media already has intro marker
					cursor.execute(f"SELECT * FROM taggings WHERE text = 'intro' AND metadata_item_id = '{rating_key}';")
					if cursor.fetchone() == None:
						#no intro marker exists so create one
						d = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
						cursor.execute("SELECT tag_id FROM taggings WHERE text = 'intro' LIMIT 1;")
						i = cursor.fetchone()
						if i == None:
							#no id yet for intro's so make one that isn't taken yet
							cursor.execute("SELECT tag_id FROM taggings ORDER BY tag_id DESC LIMIT 1;")
							i = int(cursor.fetchone()[0]) + 1
						else:
							i = i[0]
						cursor.execute(f"INSERT INTO taggings (metadata_item_id,tag_id,[index],text,time_offset,end_time_offset,thumb_url,created_at,extra_data) VALUES ({rating_key},{i},0,'intro',{value['intro_start']},{value['intro_end']},'','{d}','pv%3Aversion=5');")
					else:
						#intro marker exists so update timestamps
						cursor.execute(f"UPDATE taggings SET time_offset = '{value['intro_start']}' WHERE text = 'intro' AND metadata_item_id = '{rating_key}';")
						cursor.execute(f"UPDATE taggings SET end_time_offset = '{value['intro_end']}' WHERE text = 'intro' AND metadata_item_id = '{rating_key}';")
					#save changes
					db.commit()

			elif option in ('Genre','Writer','Director','Collection','Style', 'Mood', 'Country', 'Similar') or isinstance(value, list):
				#list of labels
				value = value or []
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
				payload[f'{option}.value'] = value or ''
				payload[f'{option}.locked'] = 1

		#upload to plex
		settings_queue.append([f'{base_url}/library/sections/{media_lib_id}/all',payload])

		result_json = file_data_json

	if path.isfile(file_thumb) and ((not type == 'episode' and import_poster == True) or (type == 'episode' and import_episode_poster == True)):
		#poster file exists for this media
		with open(file_thumb, 'rb') as f:
			data = f.read()
		poster_queue[f'{base_url}/library/metadata/{rating_key}/posters'] = data

	if path.isfile(file_art) and ((not type == 'episode' and import_art == True) or (type == 'episode' and import_episode_art == True)):
		#background file exists for this media
		with open(file_art, 'rb') as f:
			data = f.read()
		poster_queue[f'{base_url}/library/metadata/{rating_key}/arts'] = data

	return result_json, poster_queue, settings_queue, reset_queue

async def _reset_queue(reset_queue):
	async with ClientSession() as session:
		tasks = [session.put(u[0], params=u[1]) for u in reset_queue]
		await gather(*tasks)

def _reset_media(
		type: str, data: dict, media_lib_id: str, poster_queue: dict, settings_queue: dict, reset_queue: dict,
		reset_poster: bool=True, reset_art: bool=True, reset_metadata: bool=True
	):
	result_json = {}

	#get media type and define fields to unlock
	if type == 'movie':
		keys = (
			'title', 'titleSort', 'originalTitle',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio', 'tagline', 'summary',
			'Genre', 'Writer', 'Director', 'Collection'
		)
		media_type = 1

	elif type == 'show':
		keys = (
			'title', 'titleSort', 'originalTitle',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio', 'tagline', 'summary',
			'Genre', 'Collection'
		)
		media_type = 2

	elif type == 'season':
		keys = (
			'title', 'summary'
		)
		media_type = 3

	elif type == 'episode':
		keys = (
			'title', 'titleSort',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'summary',
			'Writer', 'Director'
		)
		media_type = 4

	elif type == 'artist':
		keys = (
			'title', 'titleSort', 'summary',
			'Genre', 'Style', 'Mood', 'Country', 'Collection', 'Similar'
		)
		media_type = 8

	elif type == 'album':
		keys = (
			'title', 'titleSort',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio','summary',
			'Genre', 'Style', 'Mood', 'Collection'
		)
		media_type = 9

	elif type == 'track':
		keys = (
			'title', 'originalTitle',
			'contentRating', 'userRating', 'index', 'parentIndex',
			'Mood'
		)
		media_type = 10

	else:
		#unknown type of source
		return 'Unknown source type when trying to reset data (internal error)'

	#set all data to unlocked (then, upon metadata refresh, it will all be put back as it was before the import)
	rating_key = data['ratingKey']
	payload = {
		'type': media_type,
		'id': rating_key,
		'X-Plex-Token': plex_api_token
	}
	if reset_poster == True:
		payload['thumb.locked'] = 0
	if reset_art == True:
		payload['art.locked'] = 0
	if reset_metadata == True:
		for key in keys:
			if key in ('Genre','Writer','Director','Collection','Style', 'Mood', 'Country', 'Similar'):
				payload[f'{key.lower()}.locked'] = 0
			else:
				payload[f'{key}.locked'] = 0
	result_json = payload

	reset_queue += [[f'{base_url}/library/sections/{media_lib_id}/all', payload]]

	return result_json, poster_queue, settings_queue, reset_queue

def plex_exporter_importer(
		type: str, ssn, process: list, all: bool,
		lib_id: str=None, movie_name: str=None, series_name: str=None, season_number: int=None, episode_number: int=None, artist_name: str=None, album_name: str=None, track_name: str=None
	):
	#returning non-list is for errors
	result_json, watched_map = [], {}
	poster_queue, settings_queue, reset_queue = {}, [], []

	#preparation and checks
	if not type in ('import','export','reset'):
		#type is not set to import or export
		return 'Invalid value for "type"'
	if all == True:
		if type == 'export':
			print('Exporting complete plex library')
		elif type == 'import':
			print('Importing complete plex library')
		if (lib_id, movie_name, series_name, season_number, episode_number, artist_name, album_name, track_name).count(None) > 0:
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
		if album_name != None and artist_name == None:
			#album name given but no artist name
			return '"album_name" is set but not "artist_name"'
		if track_name != None and (album_name == None or artist_name == None):
			#track name given but no album name or artist name
			return '"track_name" is set but not "album_name" or "artist_name"'

	#get user data
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers', headers={}).text
	user_ids = findall(r'(?<=userID=")\d+(?=")', shared_users)
	user_tokens = findall(r'(?<=accessToken=")\S+(?=")', shared_users)
	user_data = user_ids, user_tokens

	if type == 'export':
		method = _export_media
	elif type == 'import':
		method = _import_media
	elif type == 'reset':
		method = _reset_media
	args = {'ssn': ssn, 'user_data': user_data, 'poster_queue': poster_queue, 'settings_queue': settings_queue, 'reset_queue': reset_queue}
	if type == 'export':
		args['export_poster'] = 'poster' in process
		args['export_art'] = 'art' in process
		args['export_episode_poster'] = 'episode_poster' in process
		args['export_episode_art'] = 'episode_art' in process
		args['export_watched'] = 'watched_status' in process
		args['export_metadata'] = 'metadata' in process
		args['export_intro_markers'] = 'intro_marker' in process
		args['watched_map'] = watched_map
	elif type == 'import':
		args['import_poster'] = 'poster' in process
		args['import_art'] = 'art' in process
		args['import_episode_poster'] = 'episode_poster' in process
		args['import_episode_art'] = 'episode_art' in process
		args['import_watched'] = 'watched_status' in process
		args['import_intro_markers'] = 'intro_marker' in process
		args['import_metadata'] = 'metadata' in process
	elif type == 'reset':
		args['reset_poster'] = 'poster' in process
		args['reset_art'] = 'art' in process
		args['reset_metadata'] = 'metadata' in process
		#reset doesn't need a few of the standard arguments
		args.pop('ssn')
		args.pop('user_data')

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib_id != None and lib['key'] != lib_id:
			#a specific library is targeted and this one is not it, so skip
			continue

		#this library (or something in it) should be exported/imported
		print(lib['title'])
		if type in ('import','reset'):
			args['media_lib_id'] = lib['key']
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all')
		if lib_output.status_code != 200: continue
		lib_output = lib_output.json()['MediaContainer'].get('Metadata', [])

		if lib['type'] in ('movie','show') and type == 'export' and 'watched_status' in process:
			#create watched map for every user to reduce requests
			for user_token in user_tokens:
				user_lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'X-Plex-Token': user_token, 'type': '4' if lib['type'] == 'show' else '1'})
				if user_lib_output.status_code != 200: continue
				user_lib_output = user_lib_output.json()['MediaContainer'].get('Metadata', [])
				watched_map[user_token] = {}
				for media in user_lib_output:
					watched_map[user_token][media['ratingKey']] = media.get('viewOffset', 'viewCount' in media)

		if lib['type'] == 'movie':
			#library is movie lib; loop through every movie
			for movie in lib_output:
				if movie_name != None and movie['title'] != movie_name:
					#a specific movie is targeted and this one is not it, so skip
					continue

				print(f'	{movie["title"]}')
				#export/import movie
				result, poster_queue, settings_queue, reset_queue = method(type='movie', data=movie, **args)
				if isinstance(result, str): return result
				if result: result_json.append(result)

				if movie_name != None:
					#the targeted movie was found and processed so exit loop
					break

		elif lib['type'] == 'show':
			#library is show lib; loop through every show
			for show in lib_output:
				if series_name != None and show['title'] != series_name:
					#a specific show is targeted and this one is not it, so skip
					continue

				show_output = ssn.get(f'{base_url}{show["key"]}')
				if show_output.status_code != 200: continue
				print(f'	{show["title"]}')
				show_output = show_output.json()
				show_info = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}').json()['MediaContainer']['Metadata'][0]
				#export/import show data
				result, poster_queue, settings_queue, reset_queue = method(type='show', data=show_info, **args)
				if isinstance(result, str): return result
				if result: result_json.append(result)

				#loop through seasons of show; for season exporting/importing
				for season in show_output['MediaContainer']['Metadata']:
					if season_number != None and season['index'] != season_number:
						#a specific season is targeted and this one is not it, so skip
						continue

					#export/import season data
					result, poster_queue, settings_queue, reset_queue = method(type='season', data=season, **args)
					if isinstance(result, str): return result
					if result: result_json.append(result)

					if season_number != None:
						#the targeted season was found and processed so exit loop
						break
				else:
					if season_number != None:
						#the targeted season was not found
						return 'Season not found'

				#loop through episodes of show; for episode exporting/importing
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
					result, poster_queue, settings_queue, reset_queue = method(type='episode', data=episode, **args)
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

		elif lib['type'] == 'artist':
			#library is music lib; loop through every artist
			for artist in lib_output:
				if artist_name != None and artist['title'] != artist_name:
					#a specific artist is targeted and this one is not it, so skip
					continue

				artist_output = ssn.get(f'{base_url}{artist["key"]}')
				if artist_output.status_code != 200: continue
				print(f'	{artist["title"]}')
				artist_output = artist_output.json()
				artist_info = ssn.get(f'{base_url}/library/metadata/{artist["ratingKey"]}').json()['MediaContainer']['Metadata'][0]
				#export/import artist data
				result, poster_queue, settings_queue, reset_queue = method(type='artist', data=artist_info, **args)
				if isinstance(result, str): return result
				if result: result_json.append(result)

				#loop through albums of artist; for album exporting/importing
				for album in artist_output['MediaContainer'].get('Metadata',[]):
					if album_name != None and album['title'] != album_name:
						#a specific album is targeted and this one is not it, so skip
						continue

					#export/import album data
					result, poster_queue, settings_queue, reset_queue = method(type='album', data=album, **args)
					if isinstance(result, str): return result
					if result: result_json.append(result)

					if album_name != None:
						#the targeted album was found and processed so exit loop
						break
				else:
					if album_name != None:
						#the targeted album was not found
						return 'Album not found'

				#loop through tracks of artist; for track exporting/importing
				artist_content = ssn.get(f'{base_url}/library/metadata/{artist["ratingKey"]}/allLeaves').json()['MediaContainer'].get('Metadata',[])
				# artist_content.sort(key=lambda d: d["parentIndex"])
				for track in artist_content:
					if album_name != None and track['parentTitle'] != album_name:
						#a specific album is targeted and this one is not it; so skip
						continue

					if track_name != None and track['title'] != track_name:
						#this album is targeted but this track is not; so skip
						continue

					print(f'		{track["parentTitle"]} - D{track["parentIndex"]}T{track["index"]}	- {track["title"]}')
					#export/import track data
					result, poster_queue, settings_queue, reset_queue = method(type='track', data=track, **args)
					if isinstance(result, str): return result
					if result: result_json.append(result)

					if track_name != None:
						#the targeted track was found and processed so exit loop
						break
				else:
					if track_name != None:
						#the targeted track was not found
						return 'Track not found'

				if artist_name != None:
					#the targeted artist was found and processed so exit loop
					break
			else:
				if artist_name != None:
					#the targeted artist was not found
					return 'Artist not found'

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

	if poster_queue or settings_queue or reset_queue:
		if type == 'import':
			run(_import_queue(poster_queue=poster_queue, settings_queue=settings_queue))
			poster_queue, settings_queue = {}, {}
		elif type == 'export':
			run(_export_posters(poster_queue=poster_queue))
			poster_queue = {}
		elif type == 'reset':
			run(_reset_queue(reset_queue=reset_queue))
			reset_queue = []

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	#setup vars
	ssn = Session()
	ssn.headers.update({'Accept':'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = ArgumentParser(description='Export plex metadata to a file that can then be imported back later', epilog='If you want to use the "intro_marker" feature when importing, it is REQUIRED that the script is run on the server on which the targeted plex server is too and that the script is run using the root user (administrative user)')
	parser.add_argument('-t','--Type', choices=['import','export','reset'], required=True, type=str, help='Either export or import metadata into plex or reset import (unlock all fields)')
	parser.add_argument('-p','--Process', choices=['metadata','watched_status','poster','episode_poster','art','episode_art','intro_marker'], help='EXPORT/IMPORT ONLY: Select what to export/import; this argument can be given multiple times to select multiple things', action='append', required=True)

	#args regarding target selection
	#general selectors
	parser.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	parser.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	parser.add_argument('--AllShows', action='store_true', help='Target all show libraries')
	parser.add_argument('--AllMusic', action='store_true', help='Target all music libraries')
	parser.add_argument('-l','--LibraryName', type=str, help='Target a specific library based on it\'s name (movie and show libraries supported)')
	#movie selectors
	parser.add_argument('-m','--MovieName', type=str, help='Target a specific movie inside a movie library based on it\'s name (only accepted when -l is a movie library)')
	#show selectors
	parser.add_argument('-s','--SeriesName', type=str, help='Target a specific series inside a show library based on it\'s name (only accepted when -l is a show library)')
	parser.add_argument('-S','--SeasonNumber', type=int, help='Target a specific season inside the targeted series based on it\'s number (only accepted when -s is given) (specials is 0)')
	parser.add_argument('-e','--EpisodeNumber', type=int, help='Target a specific episode inside the targeted season based on it\'s number (only accepted when -S is given)')
	#music selectors
	parser.add_argument('-A','--ArtistName', type=str, help='Target a specific artist inside a music library based on it\'s name (only accepted when -l is a music library)')
	parser.add_argument('-d','--AlbumName', type=str, help='Target a specific album inside the targeted artist based on it\'s name (only accepted when -A is given)')
	parser.add_argument('-T','--TrackName', type=str, help='Target a specific track inside the targeted album based on it\'s name (only accepted when -d is given)')

	args = parser.parse_args()
	#get general info about targets, check for illegal arg parsing and call functions
	if args.All == True:
		#user selected --All
		if (args.LibraryName, args.MovieName, args.SeriesName, args.SeasonNumber, args.EpisodeNumber, args.ArtistName, args.AlbumName, args.TrackName, args.AllMovie, args.AllShows, args.AllMusic).count(None) > 0:
			#all is set to True but a target-specifier is also set
			parser.error('Both -a/--All and a target-specifier are set')

		response = plex_exporter_importer(type=args.Type, ssn=ssn, all=True, process=args.Process)
		if not isinstance(response, list):
			parser.error(response)
	else:
		#user is more specific
		if args.LibraryName != None and True in (args.AllMovie, args.AllShows, args.AllMusic):
			#user set library name but also library type targeter
			parser.error('Both -l/--LibraryName and --AllMovie/--AllShows/--AllMusic are set')

		sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory', [])
		for lib in sections:
			if lib['title'] == args.LibraryName or (args.AllMovie == True and lib['type'] == 'movie') or (args.AllShows == True and lib['type'] == 'show') or (args.AllMusic == True and lib['type'] == 'artist'):
				#library found
				response = plex_exporter_importer(
					type=args.Type, ssn=ssn, process=args.Process,
					all=False, lib_id=lib['key'], movie_name=args.MovieName, series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber, artist_name=args.ArtistName, album_name=args.AlbumName, track_name=args.TrackName
				)
				if not isinstance(response, list):
					if response == 'Library ID not given (lib_id)':
						parser.error('Neither -a/--All or -l/--LibraryName given')

					elif response == '"season_number" is set but not "series_name"':
						parser.error('-S/--SeasonNumber given but not -s/--SeriesName given')

					elif response == '"episode_number" is set but not "season_number" or "series_name"':
						parser.error('-e/--EpisodeNumber given but -S/--SeasonNumber or -s/--SeriesName not given')

					else:
						parser.error(response)
