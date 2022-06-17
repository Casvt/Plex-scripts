#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Keep data between two plex servers synced. Multiple things can be synced at the same time with multiuser support
Requirements (python3 -m pip install [requirement]):
	requests
	aiohttp
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every day or every week)
Example:
	Examples are assuming that main server name is 'Batman server' and backup server name is 'Robin server'
	python3 plex_sync.py -s 'Batman server' --Sync watch_history --User @all
		Sync watch history of every user from 'Batman server' to 'Robin server'
	python3 plex_sync.py -s 'Robin server' --Sync posters
		Taking 'Robin server' as the source and 'Batman server' as the sync target
		Sync the posters of the media (movies, shows and seasons)(posters of playlists and collections are synced with the Playlists and Collections action respectively)
		No need to specify users as this sync action is a general sync action and not a user specific action
	python3 plex_sync.py --SourceName 'Batman server' --User @me --User 'user2' --Sync collections --Sync playlists --Sync watch_history
		Taking 'Batman server' as the source and 'Robin server' as the sync target
		Apply the user specific sync actions (in this case playlists and watch history) to yourself and 'user2'
		Sync the collections, playlists and watch history
"""

main_plex_name = 'Main'
main_plex_ip = ''
main_plex_port = ''
main_plex_api_token = ''

backup_plex_name = 'Backup'
backup_plex_ip = ''
backup_plex_port = ''
backup_plex_api_token = ''

from os import getenv, geteuid
from os.path import join, isfile
from aiohttp import ClientSession
from asyncio import gather, run
from time import perf_counter

# Environmental Variables
main_plex_ip = getenv('main_plex_ip', main_plex_ip)
main_plex_port = getenv('main_plex_port', main_plex_port)
main_plex_api_token = getenv('main_plex_api_token', main_plex_api_token)
main_plex_name = getenv('main_plex_name', main_plex_name)
main_base_url = f"http://{main_plex_ip}:{main_plex_port}"
backup_plex_ip = getenv('backup_plex_ip', backup_plex_ip)
backup_plex_port = getenv('backup_plex_port', backup_plex_port)
backup_plex_api_token = getenv('backup_plex_api_token', backup_plex_api_token)
backup_base_url = f"http://{backup_plex_ip}:{backup_plex_port}"
backup_plex_name = getenv('backup_plex_name', backup_plex_name)

class plex_sync:
	def __init__(self, main_ssn, backup_ssn, source: str, sync: list, users: list=['@me'], sync_episode_posters: bool=True):
		#check for illegal argument parsing
		if any(s not in ('collections','posters','watch_history','playlists','intro_markers') for s in sync):
			return 'Invalid value in "sync" list'
		if not source in (main_plex_name, backup_plex_name):
			return 'Invalid value for "source"'
		if 'intro_markers' in sync and geteuid() != 0:
			return 'Script needs to be run as root when you want to sync intro_markers'

		#setup vars
		self.result_json, self.user_tokens, self.map = [], [], {}
		self.cache = {
			'source': {},
			'target': {}
		}
		self.sync = sync
		self.users = users
		self.sync_episode_posters = sync_episode_posters
		if source == main_plex_name:
			self.source_ssn = main_ssn
			self.target_ssn = backup_ssn
			self.source_base_url = main_base_url
			self.target_base_url = backup_base_url
			self.source_api_token = main_plex_api_token
			self.target_api_token = backup_plex_api_token
		elif source == backup_plex_name:
			self.source_ssn = backup_ssn
			self.target_ssn = main_ssn
			self.source_base_url = backup_base_url
			self.target_base_url = main_base_url
			self.source_api_token = backup_plex_api_token
			self.target_api_token = main_plex_api_token
		self.source_machine_id = self.__get_data('source','/')['MediaContainer']['machineIdentifier']
		self.target_machine_id = self.__get_data('target','/')['MediaContainer']['machineIdentifier']

		return

	#utility functions
	def __get_data(self, source: str, link: str, params: dict={}, refresh: bool=False, json: bool=True):
		if f'{link}{params}' in self.cache[source] and refresh == False:
			return self.cache[source][f'{link}{params}']
		else:
			if source == 'source':
				result = self.source_ssn.get(f'{self.source_base_url}{link}', params=params)
				if json == True:
					result = result.json()
			elif source == 'target':
				result = self.target_ssn.get(f'{self.target_base_url}{link}', params=params)
				if json == True:
					result = result.json()
			self.cache[source][f'{link}{params}'] = result
			return result

	def __find_on_target(self, guid: list=[], title: str='', type: str=None):
		sections = self.__get_data('target','/library/sections')['MediaContainer'].get('Directory', None)
		if sections == None: return None

		for lib in sections:
			#skip invalid lib
			if not lib['type'] in ('show','movie','artist'): continue
			#skip libs that don't contain the media type
			if type != None:
				if lib['type'] == 'show' and not type in ('episode','season','show'): continue
				if lib['type'] == 'artist' and not type in ('track','album','artist'): continue
				if lib['type'] == 'movie' and type != 'movie': continue

			if lib['type'] == 'show':
				if type == 'episode': content_type = '4'
				elif type == 'season': content_type = '3'
				else: content_type = ''
			elif lib['type'] == 'artist':
				if type == 'track': content_type = '10'
				elif type == 'album': content_type = '9'
				elif type == 'artist': content_type = '8'
			elif lib['type'] == 'movie': content_type = '1'

			if any((lib['type'] == 'show' and type == 'show', lib['type'] == 'movie' and type == 'movie')):
				lib_output = self.__get_data('target',f'/library/sections/{lib["key"]}/all', params={'includeGuids': '1'})['MediaContainer']['Metadata']
			else:
				lib_output = self.__get_data('target',f'/library/sections/{lib["key"]}/all', params={'includeGuids': '1', 'type': content_type})['MediaContainer']['Metadata']
			for entry in lib_output:
				if (guid and 'Guid' in entry and entry['Guid'] == guid) or (title and 'title' in entry and entry['title'] == title):
					#media found on target server
					return entry
		#media not found on target server
		return None

	#THE function to run
	def start_sync(self):
		#sync non-user-specific data
		if 'collections' in self.sync:
			start_time = perf_counter()
			self._collections()
			print(f'Collections time: {round(perf_counter() - start_time,3)}s')

		if 'posters' in self.sync:
			start_time = perf_counter()
			self._posters()
			print(f'Posters time: {round(perf_counter() - start_time,3)}s')

		if 'intro_markers' in self.sync:
			start_time = perf_counter()
			response = self._intro_markers()
			if isinstance(response, str): return response
			print(f'Intro markers time: {round(perf_counter() - start_time,3)}s')

		#sync user-specific data
		if 'watch_history' in self.sync:
			start_time = perf_counter()
			self._watch_history()
			print(f'Watch History time: {round(perf_counter() - start_time,3)}s')

		if 'playlists' in self.sync:
			start_time = perf_counter()
			self._playlists()
			print(f'Playlists time: {round(perf_counter() - start_time,3)}s')

		return list(set(self.result_json))

	#non-user-specific actions
	async def __process_collections(self, source_collection, target_lib, content_type):
		session = ClientSession()
		tasks = []
		print(f'	{source_collection["title"]}')

		#add collection on target server
		source_collection_content = self.__get_data('source',f'/library/collections/{source_collection["ratingKey"]}/children', params={'includeGuids': '1'})['MediaContainer']['Metadata']
		target_collection_content = []
		for entry in source_collection_content:
			target_ratingkey = self.__find_on_target(guid=entry['Guid'] if 'Guid' in entry else [], title=entry['title'] if 'title' in entry else '')
			if target_ratingkey != None:
				#media found on target server
				target_collection_content.append(target_ratingkey['ratingKey'])
		if not target_collection_content: return

		new_ratingkey = self.target_ssn.post(f'{self.target_base_url}/library/collections', params={'title': source_collection['title'], 'smart': '0', 'sectionId': target_lib['key'], 'type': content_type, 'uri': f'server://{self.target_machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(target_collection_content)}'}).json()['MediaContainer']['Metadata'][0]['ratingKey']
		#sync poster
		if 'thumb' in source_collection:
			tasks.append(session.post(f'{self.target_base_url}/library/collections/{new_ratingkey}/posters', params={'url': f'{self.source_base_url}{source_collection["thumb"]}?X-Plex-Token={self.source_api_token}','X-Plex-Token': self.target_api_token}))
		#sync settings
		payload = {
			'type': '18',
			'id': new_ratingkey,
			'titleSort.value': source_collection.get('titleSort', source_collection.get('title','')),
			'contentRating.value': source_collection.get('contentRating',''),
			'summary.value': source_collection.get('summary',''),
			'X-Plex-Token': self.target_api_token
		}
		tasks.append(session.put(f'{self.target_base_ur}/library/sections/{target_lib["key"]}/all', params=payload))
		self.result_json += target_collection_content
		#launch all the upload requests at the same time
		await gather(*tasks)
		await session.close()

	def _collections(self):
		print('Collections')

		#get sections on both servers
		source_sections = self.__get_data('source','/library/sections')['MediaContainer'].get('Directory', None)
		if source_sections == None: return 'No libraries on the source server'
		target_sections = self.__get_data('target','/library/sections')['MediaContainer'].get('Directory', None)
		if target_sections == None: return 'No libraries on the target server'

		#loop through the source libraries
		for source_lib in source_sections:
			if not source_lib['type'] in ('show','movie','artist'): continue
			if source_lib['type'] == 'show': content_type = 4
			elif source_lib['type'] == 'movie': content_type = 1
			elif source_lib['type'] == 'artist': content_type = 10

			#find the matching library on the target server
			for target_lib_entry in target_sections:
				if target_lib_entry['type'] == source_lib['type'] and target_lib_entry['title'] == source_lib['title']:
					target_lib = target_lib_entry
					break
			else:
				continue

			#get the collections in the library on both servers
			source_collections = self.__get_data('source',f'/library/sections/{source_lib["key"]}/collections')['MediaContainer'].get('Metadata', [])
			target_collections = self.__get_data('target',f'/library/sections/{target_lib["key"]}/collections')['MediaContainer'].get('Metadata', [])

			#delete all collections to keep deleted collections synced
			for target_collection in target_collections:
				self.target_ssn.delete(f'{self.target_base_url}/library/collections/{target_collection["ratingKey"]}')

			#sync each source collection with the target server
			for source_collection in source_collections:
				run(self.__process_collections(source_collection, target_lib, content_type))

		return self.result_json

	async def __process_posters(self, lib):
		if not lib['type'] in ('show','movie','artist'): return
		if lib['type'] == 'show': content_type = '4'
		elif lib['type'] == 'movie': content_type = '1'
		elif lib['type'] == 'artist': content_type = '10'

		session = ClientSession()
		tasks = []
		print(f'	{lib["title"]}')
		#sync series/season posters
		if lib['type'] == 'show':
			lib_output = self.__get_data('source',f'/library/sections/{lib["key"]}/all', params={'includeGuids': '1'})['MediaContainer']['Metadata']
			for show in lib_output:
				key = show['Guid'] if 'Guid' in show else show['title']
				if not str(key) in self.map:
					target_ratingkey = self.__find_on_target(guid=show['Guid'] if 'Guid' in show else [], title=show['title'] if 'title' in show else '', type='show')
					if target_ratingkey == None: continue
					self.map[str(key)] = target_ratingkey['ratingKey']

				tasks.append(session.post(f'{self.target_base_url}/library/metadata/{self.map[str(key)]}/posters', params={'url': f'{self.source_base_url}{show["thumb"]}?X-Plex-Token={self.source_api_token}','X-Plex-Token': self.target_api_token}))

			lib_output = self.__get_data('source',f'/library/sections/{lib["key"]}/all', params={'includeGuids': '1', 'type': '3'})['MediaContainer']['Metadata']
			for season in lib_output:
				key = season['Guid'] if 'Guid' in season else season['title']
				if not str(key) in self.map:
					target_ratingkey = self.__find_on_target(guid=season['Guid'] if 'Guid' in season else [], title=season['title'] if 'title' in season else '', type='season')
					if target_ratingkey == None: continue
					self.map[str(key)] = target_ratingkey['ratingKey']

				tasks.append(session.post(f'{self.target_base_url}/library/metadata/{self.map[str(key)]}/posters', params={'url': f'{self.source_base_url}{season["thumb"]}?X-Plex-Token={self.source_api_token}','X-Plex-Token': self.target_api_token}))

		#if said so, skip syncing episode posters
		if lib['type'] != 'show' or (self.sync_episode_posters == True and lib['type'] == 'show'):
			lib_output = self.__get_data('source',f'/library/sections/{lib["key"]}/all', params={'type': content_type, 'includeGuids': '1'})['MediaContainer']['Metadata']
			#make map of media: guids or title -> target ratingkey
			for entry in lib_output:
				key = entry['Guid'] if 'Guid' in entry else entry['title']
				if str(key) in self.map: continue

				target_ratingkey = self.__find_on_target(guid=entry['Guid'] if 'Guid' in entry else [], title=entry['title'] if 'title' in entry else '', type=entry['type'])
				if target_ratingkey == None: continue
				self.map[str(key)] = target_ratingkey['ratingKey']

			#go through every media item in the library
			for entry in lib_output:
				if not 'thumb' in entry: continue
				key = entry['Guid'] if 'Guid' in entry else entry['title']
				if not str(key) in self.map: continue
				target_ratingkey = self.map[str(key)]

				#add the request that will upload the poster to target media to a queue
				tasks.append(session.post(f'{self.target_base_url}/library/metadata/{target_ratingkey}/posters', params={'url': f'{self.source_base_url}{entry["thumb"]}?X-Plex-Token={self.source_api_token}','X-Plex-Token': self.target_api_token}))
				self.result_json.append(entry['ratingKey'])
		#launch all the upload requests at the same time
		await gather(*tasks)
		await session.close()

	def _posters(self):
		print('Posters')

		#get sections on source server
		sections = self.__get_data('source','/library/sections')['MediaContainer'].get('Directory', None)
		if sections == None: return 'No libraries on the source server'

		#process every library (at the same time) in __process_posters
		for lib in sections:
			run(self.__process_posters(lib))
		return self.result_json

	def _intro_markers(self):
		print('Intro Markers')
		from sqlite3 import connect

		#get location to database file
		db_folder = [s['value'] for s in self.__get_data('target','/:/prefs')['MediaContainer']['Setting'] if s['id'] == 'ButlerDatabaseBackupPath'][0]
		db_file = join(db_folder, 'com.plexapp.plugins.library.db')
		if not isfile(db_file):
			return '	Error: Intro Marker syncing is requested but script is not run on target server'

		#setup db connection
		db = connect(db_file)
		cursor = db.cursor()

		#loop through episodes
		sections = self.__get_data('source','/library/sections')['MediaContainer'].get('Directory',[])
		for lib in sections:
			if lib['type'] != 'show': continue
			print(f'	{lib["title"]}')
			lib_output = self.__get_data('source',f'/library/sections/{lib["key"]}/all', params={'type': '4', 'includeGuids': '1'})['MediaContainer'].get('Metadata',[])
			for episode in lib_output:
				#get markers of the episode on source
				self.result_json.append(episode['ratingKey'])
				episode_output = self.__get_data('source',f'/library/metadata/{episode["ratingKey"]}', params={'includeMarkers': '1'})['MediaContainer']['Metadata'][0].get('Marker',[])
				for marker in episode_output:
					if marker['type'] == 'intro':
						#intro marker found
						intro_start = marker['startTimeOffset']
						intro_end = marker['endTimeOffset']
						intro_id = marker['id']
						break
				else:
					#no intro marker found so skip episode
					continue

				#get ratingkey on target
				target_ratingkey = self.__find_on_target(guid=episode.get('Guid',[]), title=episode.get('title',''), type='episode')
				if target_ratingkey == None: continue
				else: target_ratingkey = target_ratingkey.get('ratingKey','')
				#set new values in db
				cursor.execute(f"UPDATE taggings SET time_offset = '{intro_start}' WHERE tag_id = '{intro_id}' AND metadata_item_id = '{target_ratingkey}';")
				cursor.execute(f"UPDATE taggings SET end_time_offset = '{intro_end}' WHERE tag_id = '{intro_id}' AND metadata_item_id = '{target_ratingkey}';")
			#save changes
			db.commit()
		return self.result_json

	#user-specific actions
	def _watch_history(self):
		print('Watch History')

		#get list of tokens (users) to apply action to
		if not self.user_tokens:
			from re import findall as re_findall

			source_shared_users = self.source_ssn.get(f'http://plex.tv/api/servers/{self.source_machine_id}/shared_servers', headers={}).text
			target_shared_users = self.target_ssn.get(f'http://plex.tv/api/servers/{self.target_machine_id}/shared_servers', headers={}).text

			#add user self if requested
			if '@me' in self.users or '@all' in self.users:
				self.user_tokens.append(['@me', self.source_api_token, self.target_api_token])

			#get data about every user (username at beginning and token at end)
			source_user_data = re_findall(r'(?<=username=").*?accessToken="\w+?(?=")', source_shared_users)
			for source_user in source_user_data:
				username = source_user.split('"')[0]
				if not '@all' in self.users and not username in self.users:
					continue
				source_token = source_user.split('"')[-1]
				target_token = re_findall(rf'username="{username}.*?accessToken="\w+?(?=")', target_shared_users)
				if target_token:
					self.user_tokens.append([username, source_token, target_token[0].split('"')[-1]])

		for user_token in self.user_tokens:
			print(f'	{user_token[0]}')

			#get sections on source server
			sections = self.__get_data('source', '/library/sections', params={'X-Plex-Token': user_token[1]})['MediaContainer'].get('Directory', [])

			#process every library (at the same time) in __process_watch_history
			for lib in sections:
				if not lib['type'] in ('show','movie','artist'): continue
				if lib['type'] == 'show': content_type = '4'
				elif lib['type'] == 'movie': content_type = '1'
				elif lib['type'] == 'artist': content_type = '10'

				handled_series = []
				print(f'		{lib["title"]}')
				#sync complete series to skip syncing every episode (reducing requests)
				if lib['type'] == 'show':
					lib_output = self.__get_data('source',f'/library/sections/{lib["key"]}/all', params={'includeGuids': '1'})['MediaContainer']['Metadata']
					for show in lib_output:
						if not (show['viewedLeafCount'] == 0 or show['viewedLeafCount'] == show['leafCount']): continue
						key = show['Guid'] if 'Guid' in show else show['title']
						if not str(key) in self.map:
							target_ratingkey = self.__find_on_target(guid=show['Guid'] if 'Guid' in show else [], title=show['title'] if 'title' in show else '', type='show')
							if target_ratingkey == None: continue
							self.map[str(key)] = target_ratingkey['ratingKey']

						if show['viewedLeafCount'] == 0:
							#mark complete series as not-viewed
							self.target_ssn.get(f'{self.target_base_url}/:/scrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': self.map[str(key)], 'X-Plex-Token': user_token[2]})
						else:
							#mark complete series as viewed
							self.target_ssn.get(f'{self.target_base_url}/:/unscrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': self.map[str(key)], 'X-Plex-Token': user_token[2]})
						handled_series.append(show['ratingKey'])

				lib_output = self.__get_data('source',f'/library/sections/{lib["key"]}/all', params={'type': content_type, 'includeGuids': '1', 'X-Plex-Token': user_token[1]})['MediaContainer']['Metadata']
				#make map of media: guids or title -> target ratingkey
				for entry in lib_output:
					if lib['type'] == 'show' and entry['grandparentRatingKey'] in handled_series: continue
					key = entry['Guid'] if 'Guid' in entry else entry['title']
					if str(key) in self.map: continue

					target_ratingkey = self.__find_on_target(guid=entry['Guid'] if 'Guid' in entry else [], title=entry['title'] if 'title' in entry else '', type=entry['type'])
					if target_ratingkey == None: continue
					self.map[str(key)] = target_ratingkey['ratingKey']

				#go through every media item in the library
				for entry in lib_output:
					key = entry['Guid'] if 'Guid' in entry else entry['title']
					if not str(key) in self.map: continue
					target_ratingkey = self.map[str(key)]

					#add the request that will set the watched status for the target media to a queue
					if 'viewOffset' in entry:
						#set media to offset (partially watched; on deck)
						self.target_ssn.get(f'{self.target_base_url}/:/progress', params={'identifier': 'com.plexapp.plugins.library', 'key': target_ratingkey, 'time': entry['viewOffset'], 'state': 'stopped', 'X-Plex-Token': user_token[2]})
					elif 'viewCount' in entry:
						#mark media as watched
						self.target_ssn.get(f'{self.target_base_url}/:/scrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': target_ratingkey, 'X-Plex-Token': user_token[2]})
					elif not 'viewCount' in entry:
						#mark media as not-watched
						self.target_ssn.get(f'{self.target_base_url}/:/unscrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': target_ratingkey, 'X-Plex-Token': user_token[2]})
					self.result_json.append(entry['ratingKey'])

		return self.result_json

	def _playlists(self):
		print('Playlists')

		#get list of tokens (users) to apply action to
		if not self.user_tokens:
			from re import findall as re_findall

			source_shared_users = self.source_ssn.get(f'http://plex.tv/api/servers/{self.source_machine_id}/shared_servers', headers={}).text
			target_shared_users = self.target_ssn.get(f'http://plex.tv/api/servers/{self.target_machine_id}/shared_servers', headers={}).text

			#add user self if requested
			if '@me' in self.users or '@all' in self.users:
				self.user_tokens.append(['@me', self.source_api_token, self.target_api_token])

			#get data about every user (username at beginning and token at end)
			source_user_data = re_findall(r'(?<=username=").*?accessToken="\w+?(?=")', source_shared_users)
			for source_user in source_user_data:
				username = source_user.split('"')[0]
				if not '@all' in self.users and not username in self.users:
					continue
				source_token = source_user.split('"')[-1]
				target_token = re_findall(rf'username="{username}.*?accessToken="\w+?(?=")', target_shared_users)
				if target_token:
					self.user_tokens.append([username, source_token, target_token[0].split('"')[-1]])

		for user_token in self.user_tokens:
			print(f'	{user_token[0]}')

			#get playlists of user
			source_playlists = self.__get_data('source','/playlists', params={'includeGuids': '1', 'X-Plex-Token': user_token[1]})['MediaContainer'].get('Metadata', [])
			target_playlists = self.__get_data('target','/playlists', params={'includeGuids': '1', 'X-Plex-Token': user_token[2]})['MediaContainer'].get('Metadata', [])

			#delete all playlists to keep deleted playlists synced
			for target_playlist in target_playlists:
				self.target_ssn.delete(f'{self.target_base_url}/playlists/{target_playlist["ratingKey"]}', params={'X-Plex-Token': user_token[2]})

			#sync source playlists to target server
			for playlist in source_playlists:
				print(f'		{playlist["title"]}')
				source_playlist_content = self.__get_data('source',f'/playlists/{playlist["ratingKey"]}/items', params={'includeGuids': '1', 'X-Plex-Token': user_token[1]})['MediaContainer'].get('Metadata', None)
				if source_playlist_content == None: continue
				#make map of media: guids or title -> target ratingkey
				for entry in source_playlist_content:
					key = entry['Guid'] if 'Guid' in entry else entry['title']
					if str(key) in self.map: continue

					target_ratingkey = self.__find_on_target(guid=entry['Guid'] if 'Guid' in entry else [], title=entry['title'] if 'title' in entry else '', type=entry['type'])
					if target_ratingkey == None: continue
					self.map[str(key)] = target_ratingkey['ratingKey']

				#go through every media item in the library
				target_playlist_content = []
				for entry in source_playlist_content:
					key = entry['Guid'] if 'Guid' in entry else entry['title']
					if not str(key) in self.map: continue
					target_ratingkey = self.map[str(key)]

					target_playlist_content.append(target_ratingkey)
					self.result_json.append(entry['ratingKey'])
				if not target_playlist_content: continue

				new_ratingkey = self.target_ssn.post(f'{self.target_base_url}/playlists', params={'type': 'video', 'title': playlist['title'], 'smart': '0', 'uri': f'server://{self.target_machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(target_playlist_content)}', 'X-Plex-Token': user_token[2]}).json()['MediaContainer']['Metadata'][0]['ratingKey']
				#sync poster
				if 'thumb' in playlist:
					self.target_ssn.post(f'{self.target_base_url}/playlists/{new_ratingkey}/posters', params={'url': f'{self.source_base_url}{playlist["thumb"]}?X-Plex-Token={self.source_api_token}'})
				#sync settings
				payload = {
					'summary': playlist.get('summary',''),
					'X-Plex-Token': self.target_api_token
				}
				self.target_ssn.put(f'{self.target_base_ur}/playlists/{new_ratingkey}', params=payload)

				self.result_json += target_playlist_content

		return self.result_json

if __name__ == '__main__':
	from requests import Session as requests_Session
	from argparse import ArgumentParser

	#setup vars
	og_start_time = perf_counter()
	main_ssn = requests_Session()
	main_ssn.headers.update({'Accept': 'application/json'})
	main_ssn.params.update({'X-Plex-Token': main_plex_api_token})
	backup_ssn = requests_Session()
	backup_ssn.headers.update({'Accept': 'application/json'})
	backup_ssn.params.update({'X-Plex-Token': backup_plex_api_token})

	#setup arg parsing
	parser = ArgumentParser(description='Keep data between two plex servers synced', epilog='If you want to use the "intro_markers" feature, it is REQUIRED that the script is run on the target server and is run using the root user (administrative user)')
	parser.add_argument('-s','--SourceName', choices=[main_plex_name, backup_plex_name], help='Select the server that the data will be pulled from. It will be uploaded on the other server (target server)', required=True)
	parser.add_argument('-S','--Sync', choices=['collections','posters','watch_history','playlists','intro_markers'], help='Select what to sync; This argument can be given multiple times', action='append', required=True, default=[])
	parser.add_argument('-u','--User', help='Apply user-specific sync actions to these users; This argument can be given multiple times; Use @me to target yourself; Use @all to target everyone', action='append', default=['@me'])
	parser.add_argument('-p','--NoEpisodePosters', help='When selecting "posters" as (one of) the sync action(s), only sync movie, series and season posters and not episode posters', action='store_false')

	args = parser.parse_args()
	#initiate class and process result
	instance = plex_sync(main_ssn=main_ssn, backup_ssn=backup_ssn, source=args.SourceName, sync=args.Sync, users=args.User, sync_episode_posters=args.NoEpisodePosters)
	if isinstance(instance, str):
		parser.error(instance)

	#run sync and process result
	response = instance.start_sync()
	if not isinstance(response, list):
		parser.error(response)

	print(f'\nTotal time: {round(perf_counter() - og_start_time,3)}s')
