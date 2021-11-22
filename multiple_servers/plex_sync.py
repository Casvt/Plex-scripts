#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Keep data between two servers synced.
Multiple things can be synced at the same time with multiuser support

Keep in mind that only media is effected by the script if it has the same name on the source AND target (e.g. 'Back to the Future 2' on both servers will work but 'Back to the Future II' + 'Back to the Future 2' not)
If you want to run this script automatically, do it every 3-7 days, as it is an intensive script for the network and servers
First set the variables below, remember the name and then run the script with --Help
For example:
	main_plex_name = 'Batman server'
	...
	backup_plex_name = 'Robin server'
	...
Arguments that can be used:
	-h/--Help:
		Show info about how to use the script; can also look here
	-S/--SourceName [name of server that's used as the source]
		REQUIRED: Select the server that serves as the source
	-T/--TargetName [name of server that's used as the target]
		REQUIRED: Select the server that will be synced to
	-s/--Sync [Collections|Posters|Watch History|Playlists]
		Select what to sync; this argument can be given multiple times to sync multiple things
		General:
			Collections: sync the collections made and the media that's inside of it
			Posters: sync the posters for media; handy for when custom posters are set
		User specific:
			Watch History: sync the watch status of media (e.g. watched/not watched/partially watched (in that case offset is copied))
			Playlists: sync all playlists the user(s) has/have made; title, summary and content are synced
	-u/--User [username]
		When given, apply user specific sync actions to these users; this argument can be given multiple times to apply to multiple users
		Use '@me' to apply the sync actions to yourself too
		Use '@all' to apply the sync actions to every user
EXAMPLES:
	python3 plex_sync.py -S 'Batman server' -T 'Robin server' --Sync 'Watch History' --User @all
		Sync watch history of every user from 'Batman server' to 'Robin server'
	python3 plex_sync.py -S 'Robin server' -T 'Batman server' --Sync Posters
		Taking 'Robin server' as the source and 'Batman server' as the sync target
		Sync the posters of the media (movies, shows and seasons)(posters of playlists and collections are synced with the Playlists and Collections action respectively)
		No need to specify users as every sync action (in this case Posters) is a general sync action and not a user specific action
	python3 plex_sync.py --SourceName 'Batman server' --TargetName 'Robin server' --User @me --User 'user2' --Sync Collections --Sync Playlists --Sync 'Watch History'
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

import requests
import re
import sys
import getopt
import threading

class sync():
	def __init__(self, source, target, pre=False, admin=False):
		#convert 'main' and 'backup' to 'source' and 'target'
		if source == 'main':
			self.source_ip = main_plex_ip
			self.source_port = main_plex_port
			self.source_api_token = main_plex_api_token
		elif source == 'backup':
			self.source_ip = backup_plex_ip
			self.source_port = backup_plex_port
			self.source_api_token = backup_plex_api_token
		if target == 'main':
			self.target_ip = main_plex_ip
			self.target_port = main_plex_port
			self.target_api_token = main_plex_api_token
		elif target == 'backup':
			self.target_ip = backup_plex_ip
			self.target_port = backup_plex_port
			self.target_api_token = backup_plex_api_token

		#set username so that it's visible to the user what the script is doing for who
		if pre == False:
			if admin == True:
				self.username = 'Admin'
			else:
				self.username = username_list[source_user_token_list[1:].index(self.source_api_token) + 1]
		#check connection and immediately set machine_id of servers too
		try:
			self.source_machine_id = requests.get('http://' + self.source_ip + ':' + self.source_port + '/', params={'X-Plex-Token': self.source_api_token}, headers={'accept': 'application/json'}).json()['MediaContainer']['machineIdentifier']
			if not self.source_machine_id:
				raise ConnectionError('can\'t connect to source plex server')
		except Exception:
			raise ConnectionError('can\'t connect to source plex server')
		try:
			self.target_machine_id = requests.get('http://' + self.target_ip + ':' + self.target_port + '/', params={'X-Plex-Token': self.target_api_token}, headers={'accept': 'application/json'}).json()['MediaContainer']['machineIdentifier']
			if not self.target_machine_id:
				raise ConnectionError('can\'t connect to target plex server')
		except Exception:
			raise ConnectionError('can\'t connect to target plex server')

		if not (self.source_ip or self.source_port or self.source_api_token) or not (self.target_ip or self.target_port or self.target_api_token):
			raise ConnectionError('required variables were not all given a value')
		#setup connection to source and target for easy use
		self.source_ssn = requests.Session()
		self.source_ssn.headers.update({'accept': 'application/json'})
		self.source_ssn.params.update({'X-Plex-Token': self.source_api_token})
		self.source_baseurl = 'http://' + self.source_ip + ':' + self.source_port
		self.target_ssn = requests.Session()
		self.target_ssn.headers.update({'accept': 'application/json'})
		self.target_ssn.params.update({'X-Plex-Token': self.target_api_token})
		self.target_baseurl = 'http://' + self.target_ip + ':' + self.target_port

	def __find_on_target(self, source_entry):
		search_output = self.target_ssn.get(self.target_baseurl + '/search', params={'query': source_entry['title']}).json()['MediaContainer']
		if 'Metadata' in search_output.keys():
			for search_result in search_output['Metadata']:
				#standard check to see if search result is same as source media
				if str(search_result['title']) == str(source_entry['title']) \
				and source_entry['type'] == search_result['type'] \
				and 'duration' in search_result.keys() \
				and 'duration' in source_entry.keys() \
				and int(search_result['duration']) >= int(source_entry['duration']) - 2500 \
				and int(search_result['duration']) <= int(source_entry['duration']) + 2500:
					#media-type specific checks to see if search result is same as source media
					if source_entry['type'] == 'episode':
						if int(search_result['index']) == int(source_entry['index']) \
						and int(search_result['parentIndex']) == int(source_entry['parentIndex']):
							return search_result
					elif source_entry['type'] == 'movie' or source_entry['type'] == 'show':
						if int(search_result['year']) == int(source_entry['year']):
							return search_result
					else:
						return search_result

	def __movie_process(self, movie):
		global source_target_mirror
		#find movie on target server
		if str(movie['ratingKey']) in source_target_mirror.keys():
			search_result = source_target_mirror[str(movie['ratingKey'])]
		else:
			search_result = self.__find_on_target(movie)
			source_target_mirror[str(movie['ratingKey'])] = search_result
		if search_result:
			#movie found on target server
			rating_key = search_result['ratingKey']
			if not 'viewOffset' in movie.keys() and 'viewCount' in movie.keys() and (not 'viewCount' in search_result.keys() or 'viewOffset' in search_result.keys()):
				#movie is marked as seen on source but not on target so update on target
				self.target_ssn.get(self.target_baseurl + '/:/scrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key})
			elif not 'viewOffset' in movie.keys() and not 'viewCount' in movie.keys() and ('viewCount' in search_result.keys() or 'viewOffset' in search_result.keys()):
				#movie is marked as not seen on source but marked as seen on target so update on target
				self.target_ssn.get(self.target_baseurl + '/:/unscrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key})
			elif 'viewOffset' in movie.keys() and (not 'viewOffset' in search_result.keys() or not search_result['viewOffset'] == movie['viewOffset']):
				#movie is not completly played but this is not reflected on target server or not at same offset
				self.target_ssn.get(self.target_baseurl + '/:/progress', params={'key': str(rating_key), 'identifier': 'com.plexapp.plugins.library', 'time': str(movie['viewOffset']), 'state': 'stopped'})

	def __show_process(self, show):
		global source_target_mirror
		#find show on target server
		if str(show['ratingKey']) in source_target_mirror.keys():
			search_result = source_target_mirror[str(show['ratingKey'])]
		else:
			search_result = self.__find_on_target(show)
			source_target_mirror[str(show['ratingKey'])] = search_result
		if search_result:
			#show found on target server
			rating_key = search_result['ratingKey']
			if show['viewedLeafCount'] == 0:
				#no episode of show is watched so just mark the whole show as not watched
				self.target_ssn.get(self.target_baseurl + '/:/unscrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': search_result['ratingKey']})
			elif show['viewedLeafCount'] == show['leafCount']:
				#every episode of the show is watched so mark the whole show as watched
				self.target_ssn.get(self.target_baseurl + '/:/scrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': search_result['ratingKey']})
			else:
				#watched and unwatched are mixed in the show
				source_series_output = self.source_ssn.get(self.source_baseurl + '/library/metadata/' + show['ratingKey'] + '/allLeaves').json()['MediaContainer']['Metadata']
				target_series_output = self.target_ssn.get(self.target_baseurl + '/library/metadata/' + rating_key + '/allLeaves').json()['MediaContainer']['Metadata']
				source_target_episode_mirror = {}
				for episode in target_series_output:
					source_target_episode_mirror[str('S' + str(episode['parentIndex']) + 'E' + str(episode['index']))] = episode
				for episode in source_series_output:
					#do this for every episode of the series
					if str('S' + str(episode['parentIndex']) + 'E' + str(episode['index'])) in source_target_episode_mirror.keys():
						target_episode = source_target_episode_mirror[str('S' + str(episode['parentIndex']) + 'E' + str(episode['index']))]
						source_target_mirror[str(episode['ratingKey'])] = target_episode
					else: continue
					if not 'viewOffset' in episode.keys() and 'viewCount' in episode.keys() and (not 'viewCount' in target_episode.keys() or 'viewOffset' in target_episode.keys()):
						#episode is marked as seen on source but not on target so update on target
						self.target_ssn.get(self.target_baseurl + '/:/scrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': target_episode['ratingKey']})
					elif not 'viewOffset' in episode.keys() and not 'viewCount' in episode.keys() and ('viewCount' in target_episode.keys() or 'viewOffset' in target_episode.keys()):
						#episode is marked as not seen on source but marked as seen on target so update on target
						self.target_ssn.get(self.target_baseurl + '/:/unscrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': target_episode['ratingKey']})
					elif 'viewOffset' in episode.keys() and (not 'viewOffset' in target_episode.keys() or not target_episode['viewOffset'] == episode['viewOffset']):
						#episode is not completly played but this is not reflected on target server or not at same offset
						self.target_ssn.get(self.target_baseurl + '/:/progress', params={'key': str(target_episode['ratingKey']), 'identifier': 'com.plexapp.plugins.library', 'time': str(episode['viewOffset']), 'state': 'stopped'})

	def watch_history(self):
		global source_target_mirror
		print(self.username + ':	Watch History')
		source_libs = self.source_ssn.get(self.source_baseurl + '/library/sections').json()['MediaContainer']
		if not 'Directory' in source_libs.keys(): return
		for directory in source_libs['Directory']:
			#do this for every directory on the source server
			print(self.username + ':		' + directory['title'])
			lib_output = self.source_ssn.get(self.source_baseurl + '/library/sections/' + str(directory['key']) + '/all').json()['MediaContainer']['Metadata']
			if directory['type'] == 'movie':
				#directory is a movie dir
				for movie in lib_output:
					#do this for every movie in the lib
					movie_process_thread = threading.Thread(target=self.__movie_process, name="Movie process", args=(movie,))
					movie_process_thread.start()
				movie_process_thread.join()

			elif directory['type'] == 'show':
				#directory is a show dir
				for show in lib_output:
					#do this for every show in the lib
					show_process_thread = threading.Thread(target=self.__show_process, name="Show process", args=(show,))
					show_process_thread.start()
				show_process_thread.join()
			else:
				#directory isn't supported yet
				print(self.username + ':			' + str(directory['title']) + ' is a ' + directory['type'] + ' directory which isn\'t supported (yet)')
				continue
		return

	def playlists(self):
		global target_playlist_keys
		global source_target_mirror
		print(self.username + ':	Playlists')
		source_playlists = self.source_ssn.get(self.source_baseurl + '/playlists').json()['MediaContainer']
		if source_playlists['size'] == 0: return
		for playlist in source_playlists['Metadata']:
			#do this for every playlist of the user on the source server
			target_playlist_keys = []
			#it would be very hard and power consuming to check if the playlist (if it already exists) is unique to the source playlist and if not to fix it,
			#thus it's easier to just delete the current target playlist (if it already exists) and create it again
			target_playlist_output = self.target_ssn.get(self.target_baseurl + '/playlists').json()['MediaContainer']
			if 'Metadata' in target_playlist_output.keys():
				for target_playlist in target_playlist_output['Metadata']:
					if target_playlist['title'] == playlist['title']:
						#playlist found on target server with same name as source playlist; removing to ensure playlist is really synced
						self.target_ssn.delete(self.target_baseurl + '/playlists/' + target_playlist['ratingKey'])
			if playlist['smart'] == False:
				print(self.username + ':		' + str(playlist['title']))
				#find the ratingKeys of the media in the source playlist on the target server
				playlist_items = self.source_ssn.get(self.source_baseurl + playlist['key']).json()['MediaContainer']
				if not 'Metadata' in playlist_items.keys(): continue
				for source_entry in playlist_items['Metadata']:
					#do this for every entry in the source playlist
					#find media on target server
					if str(source_entry['ratingKey']) in source_target_mirror.keys():
						search_result = source_target_mirror[str(source_entry['ratingKey'])]
					else:
						search_result = self.__find_on_target(source_entry)
						source_target_mirror[str(source_entry['ratingKey'])] = search_result
					if search_result:
						#media found on target server
						target_playlist_keys.append(str(search_result['ratingKey']))
					else:
						print(str(source_entry))
				#list of media ids (target) is created so make playlist with those ids, sync the poster and sync the summary if present
				target_playlist_id = self.target_ssn.post(self.target_baseurl + '/playlists', params={'type': playlist['playlistType'], 'title': playlist['title'], 'smart': '0', 'uri': 'server://' + self.target_machine_id + '/com.plexapp.plugins.library/library/metadata/' + ','.join(target_playlist_keys)}).json()['MediaContainer']['Metadata'][0]['ratingKey']
				if 'thumb' in playlist.keys():
					if '?' in playlist['thumb']: self.target_ssn.post(self.target_baseurl + '/library/metadata/' + target_playlist_id + '/posters', params={'url': self.source_baseurl + playlist['thumb'] + '&X-Plex-Token=' + self.source_api_token})
					else: self.target_ssn.post(self.target_baseurl + '/library/metadata/' + target_playlist_id + '/posters', params={'url': self.source_baseurl + playlist['thumb'] + '?X-Plex-Token=' + self.source_api_token})
				else: self.target_ssn.post(self.target_baseurl + '/library/metadata/' + target_playlist_id + '/posters', params={'url': self.source_baseurl + playlist['composite'] + '?X-Plex-Token=' + self.source_api_token})
				if 'summary' in playlist.keys():
					self.target_ssn.put(self.target_baseurl + '/playlists/' + target_playlist_id, params={'summary': str(playlist['summary'])})
			else:
				print(self.username + ':		Smart playlists aren\'t supported (yet)')
		return

	def __collection_process(self, collection):
		global source_target_mirror
		global target_collections
		col_title = collection['title']
		col_thumb = collection['thumb']
		col_ratingkey = collection['ratingKey']
		source_collection_output = self.source_ssn.get(self.source_baseurl + '/library/collections/' + col_ratingkey + '/children').json()['MediaContainer']
		#check if collection with name already exists on target server; if so, delete collection
		for target_collection in target_collections:
			if target_collection['title'] == col_title:
				#collection found on target server with same name as source collection; removing to ensure collection is really synced
				self.target_ssn.delete(self.target_baseurl + '/library/collections/' + target_collection['ratingKey'])
		if not 'Metadata' in source_collection_output.keys(): return
		target_collection_keys = {}
		for source_entry in source_collection_output['Metadata']:
			#do this for every entry in the source collection
			#find the media on the target server
			if str(source_entry['ratingKey']) in source_target_mirror.keys():
				search_result = source_target_mirror[str(source_entry['ratingKey'])]
			else:
				search_result = self.__find_on_target(source_entry)
				source_target_mirror[str(source_entry['ratingKey'])] = search_result
			if search_result:
				#media found on target server
				if not str(search_result['librarySectionID']) in target_collection_keys.keys():
					target_collection_keys[str(search_result['librarySectionID'])] = []
				target_collection_keys[str(search_result['librarySectionID'])].append(str(search_result['ratingKey']))
		target_lib_id = ''
		for target_lib_id_contestant in target_collection_keys.keys():
			if len(target_collection_keys[target_lib_id_contestant]) == len(source_collection_output['Metadata']):
				target_lib_id = str(target_lib_id_contestant)
				target_collection_keys = target_collection_keys[str(target_lib_id_contestant)]
				break
		if target_lib_id:
			#library found on target server that has every entry of source collection so adding collection there
			#create the collection on the target server, sync the summary if present and sync the poster
			target_collection_id = self.target_ssn.post(self.target_baseurl + '/library/collections', params={'type': 1, 'title': str(col_title), 'smart': 0, 'sectionId': target_lib_id, 'uri': 'server://' + self.target_machine_id + '/com.plexapp.plugins.library/library/metadata/' + ','.join(target_collection_keys)}).json()['MediaContainer']['Metadata'][0]['ratingKey']
			if '?' in col_thumb: self.target_ssn.post(self.target_baseurl + '/library/metadata/' + target_collection_id + '/posters', params={'url': self.source_baseurl + col_thumb + '&X-Plex-Token=' + self.source_api_token})
			else: self.target_ssn.post(self.target_baseurl + '/library/metadata/' + target_collection_id + '/posters', params={'url': self.source_baseurl + col_thumb + '?X-Plex-Token=' + self.source_api_token})
			if 'summary' in collection:
				self.target_ssn.put(self.target_baseurl + '/library/sections/' + target_lib_id + '/all', params={'type': '18', 'id': target_collection_id, 'summary.value': collection['summary']})

	def collections(self):
		global source_target_mirror
		global target_collections
		print(self.username + ':	Collections')
		source_libs = self.source_ssn.get(self.source_baseurl + '/library/sections').json()['MediaContainer']
		target_collections = []
		target_libs = self.target_ssn.get(self.target_baseurl + '/library/sections').json()['MediaContainer']
		if not 'Directory' in target_libs.keys(): return
		for target_lib in target_libs['Directory']:
			target_lib_collections = self.target_ssn.get(self.target_baseurl + '/library/sections/' + str(target_lib['key']) + '/collections').json()['MediaContainer']
			if not 'Metadata' in target_lib_collections.keys(): continue
			for target_collection in target_lib_collections['Metadata']:
				target_collections.append(target_collection)
		if not 'Directory' in source_libs.keys(): return
		for source_lib in source_libs['Directory']:
			#do this for every directory on the source server
			lib_id = str(source_lib['key'])
			lib_type = source_lib['type']
			print(self.username + ':		' + source_lib['title'])
			if lib_type == 'movie' or lib_type == 'show':
				#source library is a movie or show lib
				lib_col = self.source_ssn.get(self.source_baseurl + '/library/sections/' + lib_id + '/collections').json()['MediaContainer']
				if not 'Metadata' in lib_col: continue
				for collection in lib_col['Metadata']:
					#do this for every collection in the source lib
					collection_process_thread = threading.Thread(target=self.__collection_process, name="Collection process", args=(collection,))
					collection_process_thread.start()
				collection_process_thread.join()
			else:
				#directory isn't supported (yet) or can't have collections
				print(self.username + ':			' + str(source_lib['title']) + ' is a ' + source_lib['type'] + ' directory which isn\'t supported (yet) or doesn\'t allow collections')
				continue
		return

	def __poster_process(self, source_media, lib_type):
		global source_target_mirror
		#find movie/show on target server
		if str(source_media['ratingKey']) in source_target_mirror.keys():
			search_result = source_target_mirror[str(source_media['ratingKey'])]
		else:
			search_result = self.__find_on_target(source_media)
			source_target_mirror[str(source_media['ratingKey'])] = search_result
		if search_result:
			#movie/show found on target server
			rating_key = search_result['ratingKey']
			source_poster = source_media['thumb']
			self.target_ssn.post(self.target_baseurl + '/library/metadata/' + rating_key + '/posters', params={'url': self.source_baseurl + source_poster + '?X-Plex-Token=' + self.source_api_token})
			if lib_type == 'show':
				#do seasons too
				source_series_output = self.source_ssn.get(self.source_baseurl + '/library/metadata/' + source_media['ratingKey'] + '/children').json()['MediaContainer']['Metadata']
				target_series_output = self.target_ssn.get(self.target_baseurl + '/library/metadata/' + rating_key + '/children').json()['MediaContainer']['Metadata']
				source_target_season_mirror = {}
				for season in target_series_output:
					source_target_season_mirror[str(season['index'])] = season
				for season in source_series_output:
					#do this for every season of the series
					if str(season['index']) in source_target_season_mirror.keys():
						target_season = source_target_season_mirror[str(season['index'])]
					else: continue
					target_season_ratingkey = target_season['ratingKey']
					source_poster = season['thumb']
					self.target_ssn.post(self.target_baseurl + '/library/metadata/' + target_season_ratingkey + '/posters', params={'url': self.source_baseurl + source_poster + '?X-Plex-Token=' + self.source_api_token})

	def posters(self):
		global source_target_mirror
		print(self.username + ':	Posters')
		source_libs = self.source_ssn.get(self.source_baseurl + '/library/sections').json()['MediaContainer']
		if not 'Directory' in source_libs.keys(): return
		for source_lib in source_libs['Directory']:
			print(self.username + ':		' + source_lib['title'])
			lib_id = str(source_lib['key'])
			lib_type = source_lib['type']
			if lib_type  == 'movie' or lib_type == 'show':
				#source library is a movie or show library
				source_lib_output = self.source_ssn.get(self.source_baseurl + '/library/sections/' + lib_id + '/all').json()['MediaContainer']['Metadata']
				for source_media in source_lib_output:
					#do this for every media in the source lib
					poster_process_thread = threading.Thread(target=self.__poster_process, name="Poster process", args=(source_media,lib_type,))
					poster_process_thread.start()
				poster_process_thread.join()
			else:
				#directory isn't supported (yet)
				print(self.username + ':			' + str(source_lib['title']) + ' is a ' + lib_type + ' directory which isn\'t supported (yet)')
				continue
		return

if __name__ == '__main__':
	arguments, values = getopt.getopt(sys.argv[1:], 'hS:T:s:u:', ['Help', 'SourceName=', 'TargetName=', 'Sync=', 'User='])
	#don't give any value to these variables; see usage at top of file
	source_server_name = ''
	target_server_name = ''
	user_list = []
	sync_list = []
	for argument, value in arguments:
		if argument in ('-h', '--Help'):
			print('See top of file contents for usage')
			exit(0)
		if argument in ('-S', '--SourceName'):
			if value == main_plex_name: source_server_name = 'main'
			elif value == backup_plex_name: source_server_name = 'backup'
			if not source_server_name:
				print('Error: No server matched name given for ' + argument)
				exit(1)
		if argument in ('-T', '--TargetName'):
			if value == main_plex_name: target_server_name = 'main'
			elif value == backup_plex_name: target_server_name = 'backup'
			if not target_server_name:
				print('Error: No server matched name given for ' + argument)
				exit(1)
		if argument in ('-s', '--Sync'):
			sync_list.append(str(value))
		if argument in ('-u', '--User'):
			user_list.append(str(value))

	if not source_server_name or not target_server_name:
		print('Error: Arguments were not all given')
		exit(1)

	sync_session = sync(source_server_name, target_server_name, pre=True)
	username_list = ['Admin']
	#api tokens of applied users of source server
	user_share_output = requests.get('http://plex.tv/api/servers/' + sync_session.source_machine_id + '/shared_servers', params={'X-Plex-Token': sync_session.source_api_token}).text
	source_user_token_list = [sync_session.source_api_token]
	if not user_list:
		source_user_token_list.append(str(sync_session.source_api_token))
		username_list.append(str('@me'))
	elif '@all' in user_list:
		for user_data in re.findall('(?<=username=").*accessToken=".*?(?=" )', user_share_output):
			source_user_token_list.append(str(re.search('[^"]+$', user_data).group(0)))
			username_list.append(str(re.search('^.*?(?=" )', user_data).group(0)))
		source_user_token_list.append(str(sync_session.source_api_token))
		username_list.append(str('@me'))
	else:
		for user in user_list:
			try:
				if not user == '@me':
					pre_user_token = str(re.search('(?<=username="' + user + '").*accessToken=".*?(?=")', user_share_output).group(0))
					source_user_token_list.append(str(re.search('[^"]+$', pre_user_token).group(0)))
				else:
					source_user_token_list.append(str(sync_session.source_api_token))
				username_list.append(str(user))
			except AttributeError:
				print('Error: the user "' + user + '" not found on source server')
				exit(1)
	#api tokens of applied users of target server
	user_share_output = requests.get('http://plex.tv/api/servers/' + sync_session.target_machine_id + '/shared_servers', params={'X-Plex-Token': sync_session.target_api_token}).text
	target_user_token_list = [sync_session.target_api_token]
	if not user_list:
		target_user_token_list.append(str(sync_session.target_api_token))
	elif '@all' in user_list:
		for username in username_list[1:][:-1]:
			try:
				pre_user_token = re.search('username="' + username + '".*?accessToken=\".*?(?=\")', user_share_output).group(0)
				target_user_token_list.append(re.search('[^"]+$', pre_user_token).group(0))
			except AttributeError:
				print('Error: the user "' + username + '" not found on target server')
				exit(1)
		target_user_token_list.append(str(sync_session.target_api_token))
	else:
		for user in user_list:
			try:
				if not user == '@me':
					pre_user_token = str(re.search('(?<=username="' + user + '").*accessToken=".*?(?=")', user_share_output).group(0))
					target_user_token_list.append(str(re.search('[^"]+$', pre_user_token).group(0)))
				else:
					target_user_token_list.append(str(sync_session.target_api_token))
			except AttributeError:
				print('Error: the user "' + user + '" not found on target server')
				exit(1)

	loop_count = 1
	global source_target_mirror
	source_target_mirror = {}
	for source_token, target_token in zip(source_user_token_list, target_user_token_list):
		#do this for every user and also the admin
		if source_server_name == 'main': main_plex_api_token = source_token
		elif source_server_name == 'backup': backup_plex_api_token = source_token
		if target_server_name == 'main': main_plex_api_token = target_token
		elif target_server_name == 'backup': backup_plex_api_token = target_token
		if loop_count == 1: sync_session = sync(source_server_name, target_server_name, admin=True)
		else: sync_session = sync(source_server_name, target_server_name)
		for sync_type in sync_list:
			#do the actions specified
			if loop_count == 1:
				#admin actions
				if sync_type == 'Collections': sync_session.collections()
				if sync_type == 'Posters': sync_session.posters()
				continue
			if sync_type == 'Watch History': sync_session.watch_history()
			if sync_type == 'Playlists': sync_session.playlists()
		loop_count += 1
