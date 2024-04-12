#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Export plex metadata to a database file that can then be read from to import the data back (on a different plex instance)
	The following is supported:
		metadata, advanced metadata, watched status, posters, backgrounds (arts), collections, playlists, intro markers, chapter thumbnails and server settings
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script.
Notes:
	1. Under the following situations, it is REQUIRED that the script is run on the target server and that the script is run using the root user (a.k.a. administrative user):
		1. "intro_marker" when importing
		2. "chapter_thumbnail" when importing
	2. Importing chapter thumbnails on a non-linux system is not possible.
"""

plex_ip = '' #'192.168.2.15'
plex_port = '' #'32400'
plex_api_token = '' #'X8BxyR35P1WSRGQpNuz8'

# ADVANCED SETTINGS
# Hardcode the folder where the plex database is located in
# Leave empty unless really needed
database_folder = ''
plex_linux_user = 'plex'
plex_linux_group = 'plex'

from abc import ABC, abstractmethod
from datetime import datetime
from os import getenv, listdir, path
from sqlite3 import connect, Cursor
from sys import platform
from time import perf_counter
from typing import Dict, List, Tuple, Union

from requests import Session

is_linux = platform == 'linux'
if is_linux:
	from grp import getgrnam
	from os import chmod, chown, makedirs
	from pwd import getpwnam

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
database_folder = getenv('database_folder', database_folder)
base_url = f"http://{plex_ip}:{plex_port}"
if is_linux:
	plex_linux_user = getpwnam(getenv('plex_linux_user', plex_linux_user)).pw_uid
	plex_linux_group = getgrnam(getenv('plex_linux_group', plex_linux_group)).gr_gid

# Script variables
process_summary = {
	'metadata': "The standard plex metadata like title, summary, tags and more.",
	'advanced_metadata': "The advanced plex settings (metadata) for media",
	'watched_status': "The watched status of the media for every user: watched, not watched or partially watched.",
	'poster': "The (custom) poster of movies, shows, seasons, artists and albums.",
	'episode_poster': "The (custom) poster of episodes.",
	'art': "The (custom) art of movies, shows, seasons, artists and albums.",
	'episode_art': "The (custom) art of episodes.",
	'collection': "The collections in every library",
	'playlist': "The playlists of every user",
	'intro_marker': "The intro marker of episodes, which describes the beginning and end of the intro.",
	'chapter_thumbnail': "The by plex automatically generated thumbnails for chapters.",
	'server_settings': "The settings of the server"
}
data_types = {
	'collection': {
		'table_command': 
			"""
			CREATE TABLE IF NOT EXISTS collection (
				rating_key VARCHAR(15) PRIMARY KEY,
				updated_at INTEGER(10),
				title VARCHAR(255),
				titleSort VARCHAR(255),
				contentRating VARCHAR(255),
				summary TEXT,
				collectionMode VARCHAR(2),
				collectionSort VARCHAR(2),
				subtype VARCHAR(10),
				guids TEXT,
				thumb BLOB,
				art BLOB
			);
			""",
		'metadata_keys': (
			'title', 'titleSort', 'contentRating', 'summary',
			'collectionMode', 'collectionSort',
			'subtype'
		)
	},
	'server': {
		'table_command':
			"""
			CREATE TABLE IF NOT EXISTS server (
				machine_id TEXT,
				FriendlyName TEXT,
				sendCrashReports TEXT,
				PushNotificationsEnabled TEXT,
				logDebug TEXT,
				LogVerbose TEXT,
				ButlerUpdateChannel TEXT,
				ManualPortMappingMode TEXT,
				ManualPortMappingPort TEXT,
				WanTotalMaxUploadRate TEXT,
				WanPerStreamMaxUploadRate TEXT,
				FSEventLibraryUpdatesEnabled TEXT,
				FSEventLibraryPartialScanEnabled TEXT,
				watchMusicSections TEXT,
				ScheduledLibraryUpdatesEnabled TEXT,
				ScheduledLibraryUpdateInterval TEXT,
				autoEmptyTrash TEXT,
				allowMediaDeletion TEXT,
				OnDeckWindow TEXT,
				OnDeckLimit TEXT,
				OnDeckIncludePremieres TEXT,
				SmartShuffleMusic TEXT,
				MusicSeparateAlbumTypes TEXT,
				ScannerLowPriority TEXT,
				GenerateBIFBehavior TEXT,
				GenerateIntroMarkerBehavior TEXT,
				GenerateChapterThumbBehavior TEXT,
				LoudnessAnalysisBehavior TEXT,
				MusicAnalysisBehavior TEXT,
				LocationVisibility TEXT,
				EnableIPv6 TEXT,
				secureConnections TEXT,
				customCertificatePath TEXT,
				customCertificateKey TEXT,
				customCertificateDomain TEXT,
				PreferredNetworkInterface TEXT,
				DisableTLSv1_0 TEXT,
				GdmEnabled TEXT,
				WanPerUserStreamCount TEXT,
				LanNetworksBandwidth TEXT,
				MinutesAllowedPaused TEXT,
				TreatWanIpAsLocal TEXT,
				RelayEnabled TEXT,
				customConnections TEXT,
				allowedNetworks TEXT,
				WebHooksEnabled TEXT,
				TranscoderQuality TEXT,
				TranscoderTempDirectory TEXT,
				TranscoderThrottleBuffer TEXT,
				TranscoderH264BackgroundPreset TEXT,
				TranscoderToneMapping TEXT,
				TranscoderCanOnlyRemuxVideo TEXT,
				HardwareAcceleratedCodecs TEXT,
				HardwareAcceleratedEncoders TEXT,
				TranscodeCountLimit TEXT,
				DlnaEnabled TEXT,
				DlnaClientPreferences TEXT,
				DlnaReportTimeline TEXT,
				DlnaDefaultProtocolInfo TEXT,
				DlnaDeviceDiscoveryInterval TEXT,
				DlnaAnnouncementLeaseTime TEXT,
				DlnaDescriptionIcons TEXT,
				ButlerStartHour TEXT,
				ButlerEndHour TEXT,
				ButlerTaskBackupDatabase TEXT,
				ButlerDatabaseBackupPath TEXT,
				ButlerTaskOptimizeDatabase TEXT,
				ButlerTaskCleanOldBundles TEXT,
				ButlerTaskCleanOldCacheFiles TEXT,
				ButlerTaskRefreshLocalMedia TEXT,
				ButlerTaskRefreshLibraries TEXT,
				ButlerTaskUpgradeMediaAnalysis TEXT,
				ButlerTaskRefreshPeriodicMetadata TEXT,
				ButlerTaskDeepMediaAnalysis TEXT,
				ButlerTaskReverseGeocode TEXT,
				ButlerTaskGenerateAutoTags TEXT,
				CinemaTrailersType TEXT,
				CinemaTrailersFromLibrary TEXT,
				CinemaTrailersFromTheater TEXT,
				CinemaTrailersFromBluRay TEXT,
				CinemaTrailersPrerollID TEXT,
				GlobalMusicVideoPath TEXT
			)
			""",
		'metadata_keys': (
			'FriendlyName','sendCrashReports','PushNotificationsEnabled','logDebug','LogVerbose','ButlerUpdateChannel',
			'ManualPortMappingMode', 'ManualPortMappingPort', 'WanTotalMaxUploadRate', 'WanPerStreamMaxUploadRate',
			'FSEventLibraryUpdatesEnabled', 'FSEventLibraryPartialScanEnabled', 'watchMusicSections', 'ScheduledLibraryUpdatesEnabled', 'ScheduledLibraryUpdateInterval', 'autoEmptyTrash', 'allowMediaDeletion', 'OnDeckWindow', 'OnDeckLimit', 'OnDeckIncludePremieres', 'SmartShuffleMusic', 'MusicSeparateAlbumTypes', 'ScannerLowPriority', 'GenerateBIFBehavior', 'GenerateIntroMarkerBehavior', 'GenerateChapterThumbBehavior', 'LoudnessAnalysisBehavior', 'MusicAnalysisBehavior', 'LocationVisibility',
			'EnableIPv6', 'secureConnections', 'customCertificatePath', 'customCertificateKey', 'customCertificateDomain', 'PreferredNetworkInterface', 'DisableTLSv1_0', 'GdmEnabled', 'WanPerUserStreamCount', 'LanNetworksBandwidth', 'MinutesAllowedPaused', 'TreatWanIpAsLocal', 'RelayEnabled', 'customConnections', 'allowedNetworks', 'WebHooksEnabled',
			'TranscoderQuality', 'TranscoderTempDirectory', 'TranscoderThrottleBuffer', 'TranscoderH264BackgroundPreset', 'TranscoderToneMapping', 'TranscoderCanOnlyRemuxVideo', 'HardwareAcceleratedCodecs', 'HardwareAcceleratedEncoders', 'TranscodeCountLimit',
			'DlnaEnabled', 'DlnaClientPreferences', 'DlnaReportTimeline', 'DlnaDefaultProtocolInfo', 'DlnaDeviceDiscoveryInterval', 'DlnaAnnouncementLeaseTime', 'DlnaDescriptionIcons',
			'ButlerStartHour', 'ButlerEndHour', 'ButlerTaskBackupDatabase', 'ButlerDatabaseBackupPath', 'ButlerTaskOptimizeDatabase', 'ButlerTaskCleanOldBundles', 'ButlerTaskCleanOldCacheFiles', 'ButlerTaskRefreshLocalMedia', 'ButlerTaskRefreshLibraries', 'ButlerTaskUpgradeMediaAnalysis', 'ButlerTaskRefreshPeriodicMetadata', 'ButlerTaskDeepMediaAnalysis', 'ButlerTaskReverseGeocode', 'ButlerTaskGenerateAutoTags',
			'CinemaTrailersType', 'CinemaTrailersFromLibrary', 'CinemaTrailersFromTheater', 'CinemaTrailersFromBluRay', 'CinemaTrailersPrerollID', 'GlobalMusicVideoPath'
		)
	},
	'playlist': {
		'table_command':
			"""
			CREATE TABLE IF NOT EXISTS playlist (
				rating_key VARCHAR(15) PRIMARY KEY,
				updated_at INTEGER(8),
				user_id INTEGER(10),
				title VARCHAR(255),
				summary TEXT,
				playlistType VARCHAR(15),
				guids TEXT,
				thumb BLOB,
				art BLOB
			);
			""",
		'metadata_keys': (
			'title', 'summary'
		)
	},
	'movie': {},
	'show': {},
	'artist': {}
}
types = ('export', 'import', 'reset')

class RequestCache:
	def __init__(self) -> None:
		self.ssn: Session = None
		self.__machine_id: str = None
		self.__sections: List[dict] = None
		self.__media_infos: Dict[str, dict] = {}

	@property
	def machine_id(self) -> str:
		if self.__machine_id is None:
			self.__machine_id = self.ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
		return self.__machine_id

	@property
	def sections(self) -> List[dict]:
		if self.__sections is None:
			self.__sections = self.ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory', [])
		return self.__sections
	
	def media_info(self, rating_key: str) -> Union[dict, None]:
		if not rating_key in self.__media_infos:
			r = self.ssn.get(
				f'{base_url}/library/metadata/{rating_key}',
				params={'includeGuids': '1', 'includeMarkers': '1', 'includeChapters': '1', 'includePreferences': '1'}
			)
			if r.ok:
				self.__media_infos[rating_key] = r.json()['MediaContainer']['Metadata'][0]
			else:
				self.__media_infos[rating_key] = None
		return self.__media_infos[rating_key]
cache = RequestCache()

class GetTargetedMedia:
	def __init__(self,
	    all_media: bool, all_movie: bool, all_show: bool, all_music: bool,
		library_names: List[str],
		movie_names: List[str],
		series_name: str, season_number: int, episode_number: int,
		artist_name: str, album_name: str, track_name: str,
		ssn: Session, verbose: bool=False
	) -> None:
		self.results: List[dict] = []
		
		self.all_media = all_media
		self.all_movie = all_movie
		self.all_show = all_show
		self.all_music = all_music
		self.library_names = library_names
		self.movie_names = movie_names
		self.series_name = series_name
		self.season_number = season_number
		self.episode_number = episode_number
		self.artist_name = artist_name
		self.album_name = album_name
		self.track_name = track_name
		self.ssn = ssn
		self.verbose = verbose

	def iter(self) -> dict:
		if self.results:
			for result in self.results:
				yield result
			return
		
		for lib in cache.sections:
			if not (
				lib['type'] in data_types # lib is supported
				and (
					self.all_media
					or (self.all_movie and lib['type'] == 'movie')
					or (self.all_show and lib['type'] == 'show')
					or (self.all_music and lib['type'] == 'artist')
					or (self.library_names is not None and lib['title'] in self.library_names)
				)
			):
				# A specific library is targeted and this one isn't it so skip
				continue

			print(lib['title'])
			lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'includeGuids': '1'})
			if not lib_output.ok: continue
			lib_output = lib_output.json()['MediaContainer'].get('Metadata', [])

			if lib['type'] == 'movie':
				for movie in lib_output:
					if self.movie_names is not None and not movie['title'] in self.movie_names:
						continue
					
					if self.verbose: print(f'	{movie["title"]}')
					self.results.append(movie)
					yield movie
					
			elif lib['type'] == 'show':
				for show in lib_output:
					if self.series_name is not None and show['title'] != self.series_name:
						continue
					
					if self.verbose: print(f'	{show["title"]}')
					# Process show
					show_info = cache.media_info(show['ratingKey'])
					if show_info:
						self.results.append(show_info)
						yield show_info
					else:
						continue

					# Process seasons
					season_info = self.ssn.get(f'{base_url}{show["key"]}', params={'includeGuids': '1'})
					if not season_info.ok: continue
					season_info = season_info.json()['MediaContainer'].get('Metadata', [])
					for season in season_info:
						if self.season_number is not None and season['index'] != self.season_number:
							continue
						
						self.results.append(season)
						yield season
						
						if self.season_number is not None:
							break
					else:
						if self.season_number is not None:
							return 'Season not found'

					# Process episodes
					episode_info = ssn.get(
						f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves', params={'includeGuids': '1'}
					).json()['MediaContainer'].get('Metadata', [])
					for episode in episode_info:
						if self.season_number is not None and episode['parentIndex'] != self.season_number:
							continue
						if self.episode_number is not None and episode['index'] != self.episode_number:
							continue
						
						if self.verbose: print(f'		S{episode["parentIndex"]}E{episode["index"]} - {episode["title"]}')
						self.results.append(episode)
						yield episode
						
						if self.episode_number is not None:
							break
					else:
						if self.episode_number is not None:
							return 'Episode not found'
					
					if self.series_name is not None:
						break
				else:
					if self.series_name is not None:
						return 'Series not found'

			elif lib['type'] == 'artist':
				for artist in lib_output:
					if self.artist_name is not None and artist['title'] != self.artist_name:
						continue
					
					if self.verbose: print(f'	{artist["title"]}')
					# Process artist
					artist_info = cache.media_info(artist['ratingKey'])
					if artist_info:
						self.results.append(artist_info)
						yield artist_info
					else:
						continue

					# Process albums
					album_info = self.ssn.get(f'{base_url}{artist["key"]}', params={'includeGuids': '1'})
					if not album_info.ok: continue
					album_info = album_info.json()['MediaContainer'].get('Metadata', [])
					for album in album_info:
						if self.album_name is not None and album['title'] != self.album_name:
							continue
						
						self.results.append(album)
						yield album
						
						if self.album_name is not None:
							break
					else:
						if self.album_name is not None:
							return 'Album not found'

					# Process tracks
					track_info = ssn.get(
						f'{base_url}/library/metadata/{artist["ratingKey"]}/allLeaves', params={'includeGuids': '1'}
					).json()['MediaContainer'].get('Metadata', [])
					for track in track_info:
						if self.album_name is not None and track['parentTitle'] != self.album_name:
							continue
						if self.track_name is not None and track['title'] != self.track_name:
							continue
						
						if self.verbose: print(f'		D{track["parentIndex"]}T{track["index"]} - {track["title"]}')
						self.results.append(track)
						yield track
						
						if self.track_name is not None:
							break
					else:
						if self.track_name is not None:
							return 'Track not found'
					
					if self.artist_name is not None:
						break
				else:
					if self.artist_name is not None:
						return 'Artist not found'
			else:
				print('	Library not supported')

class Type(ABC):
	@abstractmethod
	def run(self) -> Union[List[int], str]:
		pass

class Export(Type):
	def __init__(self,
	    ssn: Session,
		cursor: Cursor, plex_cursor: Cursor,
		process: List[str],
		user_data: Tuple[tuple, tuple],
		media_getter: GetTargetedMedia,
		verbose: bool=False
	) -> None:
		self.ssn = ssn
		self.cursor = cursor
		self.plex_cursor = plex_cursor
		self.process = process
		self.user_data = user_data
		self.media_getter = media_getter
		self.verbose = verbose

		self.function_mapping = {
			'server_settings': self._server_settings,
			'collection': self._collection,
			'playlist': self._playlist,
			'metadata': self._metadata,
			'advanced_metadata': self._advanced_metadata
		}
		return

	def _server_settings(self) -> Union[List, str]:
		print('Server Settings')
		
		# Create table if it doesn't exist
		self.cursor.execute(data_types['server']['table_command'])
		
		# Delete old entries as they could be outdated
		self.cursor.execute("DELETE FROM server WHERE machine_id = ?", (cache.machine_id,))
		
		# Build new db entry
		db_info = {
			'machine_id': cache.machine_id
		}
		prefs = self.ssn.get(f'{base_url}/:/prefs').json()['MediaContainer']['Setting']
		for pref in prefs:
			if not pref['id'] in data_types['server']['metadata_keys']: continue
			db_info[pref['id']] = pref['value']
		
		# Add to database
		self.cursor.execute(f"""
			INSERT INTO server({",".join(db_info.keys())})
			VALUES ({",".join(['?'] * len(db_info))});
		""", db_info.values())

		return []

	def _collection(self) -> Union[List[int], str]:
		print('Collections')
		result: List[int] = []

		# Create table if it doesn't exist
		self.cursor.execute(data_types['collection']['table_command'])
		
		# If there already is a table with content (updating the db), use the updated_at timestamp to reduce work (updating)
		self.cursor.execute("SELECT rating_key, updated_at FROM collection;")
		timestamp_map = dict(self.cursor)
		
		# Go through every collection on the server
		for lib in cache.sections:
			collections: List[dict] = self.ssn.get(
				f'{base_url}/library/sections/{lib["key"]}/collections'
			).json()['MediaContainer'].get('Metadata', [])
			for collection in collections:
				if collection.get('smart') == '1': continue
				updated_at = timestamp_map.get(collection['ratingKey'])
				if updated_at == collection.get('updatedAt', 0):
					# Skip because it hasn't been updated since last export
					continue

				elif updated_at:
					# Existing record is outdated so delete
					self.cursor.execute("DELETE FROM collection WHERE rating_key = ?", (collection['ratingKey'],))
				
				else:
					# Collection either hasn't been added to db yet or has been imported after exporting
					self.cursor.execute("DELETE FROM collection WHERE title = ?", (collection['title'],))

				# Fetch info of collection and build up database entry
				data: dict = self.ssn.get(
					f'{base_url}/library/collections/{collection["ratingKey"]}',
					params={'includePreferences': '1'}
				).json()['MediaContainer']['Metadata'][0]

				collection_content = self.ssn.get(
					f'{base_url}/library/collections/{collection["ratingKey"]}/children',
					params={'includeGuids': '1'}
				).json()['MediaContainer'].get('Metadata', [])

				db_info = {
					'rating_key': collection['ratingKey'],
					'updated_at': collection.get('updatedAt', 0),
					'guids': "|".join(str(m["Guid"]) for m in collection_content if 'Guid' in m)
				}
				for key in data_types['collection']['metadata_keys']:
					if key == 'titleSort':
						db_info[key] = data.get('titleSort', data.get('title', ''))
					else:
						db_info[key] = data.get(key)
				
				for poster_type in ('thumb', 'art'):
					if poster_type in data:
						r = self.ssn.get(f'{base_url}{data[poster_type]}')
						db_info[poster_type] = r.content if r.ok else None
				
				comm = f"""
					INSERT INTO collection({",".join(db_info.keys())})
					VALUES ({",".join(['?'] * len(db_info))});
				"""
				self.cursor.execute(comm, list(db_info.values()))
				result.append(collection['ratingKey'])

		return result

	def _playlist(self) -> Union[List[int], str]:
		print('Playlists')
		result: List[int] = []
		
		# Create table if it doesn't exist
		self.cursor.execute(data_types['playlist']['table_command'])
	
		# If there already is a table with content (updating the db), use the updated_at timestamp to reduce work (updating)
		self.cursor.execute("SELECT rating_key, updated_at FROM playlist;")
		timestamp_map = dict(self.cursor)
		
		# Export playlists of all users
		complete_user_data = (list(self.user_data[0]) + ['_admin'], list(self.user_data[1]) + [plex_api_token])
		for user_id, user_token in zip(*complete_user_data):
			self.ssn.params.update({'X-Plex-Token': user_token})
			playlists: List[dict] = self.ssn.get(f'{base_url}/playlists').json()['MediaContainer'].get('Metadata', [])
			for playlist in playlists:
				# Filter what to export
				if playlist.get('smart'): continue
				updated_at = timestamp_map.get(playlist['ratingKey'])
				if updated_at == playlist.get('updatedAt', 0):
					# Skip because it hasn't been updated since last export
					continue
				self.cursor.execute("DELETE FROM playlist WHERE rating_key = ?", (playlist['ratingKey'],))
				
				playlist_content = self.ssn.get(
					f'{base_url}{playlist["key"]}',
					params={'includeGuids': '1'}
				).json()['MediaContainer'].get('Metadata', [])
				
				db_info = {
					'rating_key': playlist['ratingKey'],
					'updated_at': playlist.get('updatedAt', 0),
					'user_id': user_id,
					'title': playlist.get('title'),
					'summary': playlist.get('summary'),
					'playlistType': playlist.get('playlistType'),
					'guids': "|".join(str(m['Guid']) for m in playlist_content if 'Guid' in m)
				}
				
				for poster_type in ('thumb', 'art'):
					if poster_type in playlist:
						r = self.ssn.get(f'{base_url}{playlist[poster_type]}')
						db_info[poster_type] = r.content if r.ok else None

				comm = f"""
					INSERT INTO playlist({",".join(db_info.keys())})
					VALUES ({",".join(['?'] * len(db_info))})
				"""
				self.cursor.execute(comm, list(db_info.values()))
				result.append(playlist['ratingKey'])
				
		return result
	
	def _metadata(self) -> List[int]:
		print('Metadata')
		for media in self.media_getter.iter():
			pass
		return []

	def _advanced_metadata(self) -> List[int]:
		print('Advanced metadata')
		for media in self.media_getter.iter():
			pass
		return []

	def run(self) -> Union[List[int], str]:
		result: List[int] = []
		
		for process, func in self.function_mapping.items():
			if process in self.process:
				response = func()
				if isinstance(response, str):
					return response
				result += response

		return result



class Import(Type):
	def __init__(self,
	    ssn: Session,
		cursor: Cursor, plex_cursor: Cursor,
		process: List[str],
		user_data: Tuple[tuple, tuple],
		media_getter: GetTargetedMedia,
		verbose: bool=False
	) -> None:
		self.ssn = ssn
		self.cursor = cursor
		self.plex_cursor = plex_cursor
		self.process = process
		self.user_data = user_data
		self.media_getter = media_getter
		self.verbose = verbose
		return

	def run(self) -> Union[List[int], str]:
		pass



class Reset(Type):
	def __init__(self,
	    ssn: Session,
	    verbose: bool=False
	) -> None:
		self.ssn = ssn
		self.verbose = verbose
		return

	def run(self) -> Union[List[int], str]:
		pass



def plex_exporter_importer(
	ssn: Session, type: str, process: List[str],
	all_media: bool, all_movie: bool, all_show: bool, all_music: bool,
	library_names: List[str],
	movie_names: List[str],
	series_name: str, season_number: int, episode_number: int,
	artist_name: str, album_name: str, track_name: str, 
	verbose: bool=False, location: str=None
) -> Union[List[int], str]:
	result: List[int] = []
	cursor, plex_cursor = None, None
	cache.ssn = ssn
	


	# Check if argument parsing is correct (and logical)
	if not type in types:
		return 'Invalid value for "type"'
	if not is_linux and type == 'import' and 'chapter_thumbnails' in process:
		return 'Importing chapter thumbnails on a non-linux system is not supported'
	if any(not p in process_summary.keys() for p in process):
		return 'One of the processes selected is invalid'

	if all_media:
		if (
			all_movie or all_show or all_music
			or library_names
			or movie_names
			or series_name or season_number is not None or episode_number is not None
			or artist_name or album_name or track_name
    	):
			return 'Both "all_media" and a target-specifier are set'
	else:
		if (any(p in process for p in ('metadata', 'advanced_metadata', 'watched_status', 'poster', 'episode_poster', 'art', 'episode_art', 'intro_marker', 'chapter_thumbnail'))
		and not (all_movie or all_show or all_music or library_names)):
			return '"all_media" is set to False but no target-specifier is given'
		if season_number is not None and series_name is None:
			return '"season_number" is set but not "series_name"'
		if episode_number is not None and None in (series_name, season_number):
			return '"episode_number" is set but not "series_name" or "season_number"'
		if album_name is not None and artist_name is None:
			return '"album_name" is set but not "artist_name"'
		if track_name is not None and None in (artist_name, album_name):
			return '"track_name" is set but not "artist_name" or "album_name"'
	


	# Setup database connections
	database_file = f'{path.splitext(path.abspath(__file__))[0]}.db' # e.g. plex_exporter_importer.db
	if type == 'export':
		if path.isdir(location):
			database_file = path.join(location, database_file)
				
		elif location.endswith('.db'):
			database_file = location
		
		else:
			return 'Location not found'

		if path.isfile(database_file):
			print(f'Exporting to {database_file} (Updating)')
		else:
			print(f'Exporting to {database_file}')
	
	elif type == 'import':
		if path.isfile(location):
			if location.endswith('.db'):
				database_file = location
				print(f'Importing from {database_file}')
			else:
				return 'Invalid location'
		else:
			return 'Location not found'
		
	elif type == 'reset':
		database_file = None
		
	if ('intro_marker' in process and type == 'import') or ('chapter_thumbnail' in process and type in ('import', 'export')):
		# Importing intro markers or importing/exporting chapter thumbnails requires access to the plex database
		if not database_folder:
			for s in ssn.get(f'{base_url}/:/prefs').json()['MediaContainer']['Setting']:
				if s['id'] == 'ButlerDatabaseBackupPath':
					database_folder = s['value']
					break
		plex_database_file = path.join(database_folder, 'com.plexapp.plugins.library.db')
		if not path.isfile(plex_database_file):
			return 'Intro marker or chapter thumbnail importing or chapter thumbnail exporting requires script to be run on the target server or the value of the variable "database_folder" is invalid'

		# Importing intro markers or chapter thumbnails requires the script to be run as root
		if type == 'import':
			if is_linux:
				from os import geteuid
				is_root = geteuid() == 0
			else:
				import ctypes
				is_root = ctypes.windll.shell32.IsUserAnAdmin() == 1
			if not is_root:
				return 'Intro marker or chapter thumbnail importing requires the script to be run as root (a.k.a. administrator)'
		
		plex_cursor = connect(plex_database_file, timeout=10.0).cursor()
	cursor = connect(database_file, timeout=10.0).cursor()



	# Build summary
	# What's going to be processed
	summary = f"You're going to {type} the following:\n"
	summary += ''.join(f'	{process_summary.get(p, p)}\n' for p in process)

	# What's going to be targeted
	if any(not p in ('server_settings', 'collection', 'playlist') for p in process):
		summary += 'The media processes are done for '
		if all_media: summary += 'your complete plex library'
		elif True in (all_movie, all_show, all_music):
			targeted_libs = []
			if all_movie: targeted_libs.append('movie')
			if all_show: targeted_libs.append('show')
			if all_music: targeted_libs.append('music')
			summary += f"all {'/'.join(targeted_libs)} libraries"
		else:
			if len(library_names) > 1:
				summary += f'the libraries {", ".join(library_names)}'
			else:
				summary += f'the library {library_names[0]}'
			if movie_names:
				summary += f' -> {", ".join(movie_names)}'
			elif series_name:
				summary += f' -> {series_name}'
				if season_number:
					summary += f' -> Season {season_number}'
					if episode_number is not None: summary += f' -> Episode {episode_number}'
			elif artist_name:
				summary += f' -> {artist_name}'
				if album_name:
					summary += f' -> Album {album_name}'
					if track_name: summary += f' -> Track {track_name}'
		summary += '.\n'
	print(summary)
	
	
	
	# Gather user info
	shared_users = ssn.get(f'http://plex.tv/api/servers/{cache.machine_id}/shared_servers').text
	result = map(lambda r: r.split('"')[0:3:2], shared_users.split('userID="')[1:])
	user_data = tuple(zip(*result)) or ((), ())


	
	# Create instance of class of type
	media_getter = GetTargetedMedia(
		all_media, all_movie, all_show, all_music,
		library_names,
		movie_names,
		series_name, season_number, episode_number,
		artist_name, album_name, track_name, 
		ssn, verbose
	)
	if type == 'export':
		runner = Export(ssn, cursor, plex_cursor, process, user_data, media_getter, verbose)
	elif type == 'import':
		runner = Import(ssn, cursor, plex_cursor, process, user_data, media_getter, verbose)
	else:
		runner = Reset(ssn, verbose)
	
	# Start
	try:
		result = runner.run()
		cursor.connection.commit()
		if plex_cursor is not None:
			plex_cursor.connection.commit()
		return result
	except Exception as e:
		print('Shutting down...')
		cursor.connection.commit()
		if plex_cursor is not None:
			plex_cursor.connection.commit()
		print('Progress saved')
		print('AN ERROR OCCURED. ALL YOUR PROGRESS IS SAVED. PLEASE SHARE THE FOLLOWING WITH THE DEVELOPER:')
		raise e

if __name__ == "__main__":
	from argparse import ArgumentParser, RawTextHelpFormatter

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept':'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	# Setup arg parsing
	epilog = """-------------------
EPILOG

-p/--Process
{p}

	Notes:
	1. Under the following situations, it is REQUIRED that the script is run on the target server and that the script is run using the root user (a.k.a. administrative user):
		1. "intro_marker" when importing
		2. "chapter_thumbnail" when importing
	2. Importing chapter thumbnails on a non-linux system is not possible.

-L/--Location
	When using the script, you might want to influence how the script handles the database file,
	which you can set using the -L/--Location option. See:

	When exporting and not giving this argument, the database file will be put in the same folder as the script.
	When exporting and giving a path to a folder, the database file will be put in that folder.
	When exporting and giving a path to a database file, that database file will be used to put the data in or will be updated if data is already in it (STRONGLY RECOMMENDED IF POSSIBLE)
	When importing and giving a path to a database file, that database file will be read and used as the source of the data that will be applied
""".format(p="\n".join(map(lambda k: f'	{k[0]}: {k[1]}', process_summary.items())))

	parser = ArgumentParser(formatter_class=RawTextHelpFormatter, description='Export plex metadata to a database file that can then be read from to import the data back (on a different plex instance)\n\n', epilog=epilog)
	parser.add_argument('-t','--Type', choices=types, required=True, type=str, help='Either export/import plex metadata or reset import (unlock all fields)')
	parser.add_argument('-p','--Process', choices=process_summary.keys(), help='EXPORT/IMPORT ONLY: Select what to export/import; this argument can be given multiple times to select multiple things', action='append', required=True)
	parser.add_argument('-L','--Location', type=str, help='SEE EPILOG', default=path.dirname(path.abspath(__file__)))
	parser.add_argument('-v','--Verbose', help='Make script more verbose\n\nTarget Selectors', action='store_true')

	# Args regarding target selection
	# General selectors
	parser.add_argument('-a','--All', action='store_true', help='Target all media items in each library (use with care!)')
	parser.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	parser.add_argument('--AllShow', action='store_true', help='Target all show libraries')
	parser.add_argument('--AllMusic', action='store_true', help='Target all music libraries')
	parser.add_argument('-l','--LibraryName', type=str, help='Target a specific library based on it\'s name (movie, show and music libraries supported); this argument can be given multiple times to select multiple libraries\n\nMovie Selectors', action='append', default=None)
	# Movie selectors
	parser.add_argument('-m','--MovieName', type=str, help='Target a specific movie inside a movie library based on it\'s name (only accepted when -l is a movie library); this argument can be given multiple times to select multiple movies\n\nShow Selectors', action='append', default=None)
	# Show selectors
	parser.add_argument('-s','--SeriesName', type=str, help='Target a specific series inside a show library based on it\'s name (only accepted when -l is a show library)')
	parser.add_argument('-S','--SeasonNumber', type=int, help='Target a specific season inside the targeted series based on it\'s number (only accepted when -s is given) (specials is 0)')
	parser.add_argument('-e','--EpisodeNumber', type=int, help='Target a specific episode inside the targeted season based on it\'s number (only accepted when -S is given)\n\nMusic Selectors')
	# Music selectors
	parser.add_argument('-A','--ArtistName', type=str, help='Target a specific artist inside a music library based on it\'s name (only accepted when -l is a music library)')
	parser.add_argument('-d','--AlbumName', type=str, help='Target a specific album inside the targeted artist based on it\'s name (only accepted when -A is given)')
	parser.add_argument('-T','--TrackName', type=str, help='Target a specific track inside the targeted album based on it\'s name (only accepted when -d is given)')

	args = parser.parse_args()

	start_time = perf_counter()
	response = plex_exporter_importer(
		ssn=ssn, type=args.Type, process=args.Process,
		all_media=args.All, all_movie=args.AllMovie, all_show=args.AllShow, all_music=args.AllMusic,
		library_names=args.LibraryName,
		movie_names=args.MovieName,
		series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber,
		artist_name=args.ArtistName, album_name=args.AlbumName, track_name=args.TrackName,
		verbose=args.Verbose, location=args.Location
	)
	print(f'Time: {perf_counter() - start_time:.3f}s')
	if not isinstance(response, list):
		if response == 'Both "all_media" and a target-specifier are set':
			parser.error('Both -a/--All and a target-specifier are set')
		elif response == '"all_media" is set to False but no target-specifier is given':
			parser.error('-a/--All is not set but also no target-specifier is set')
		elif response == '"season_number" is set but not "series_name"':
			parser.error('-S/--SeasonNumber is set but not -s/--SeriesName')
		elif response == '"episode_number" is set but not "series_name" or "season_number"':
			parser.error('-e/--EpisodeNumber is set but not -s/--SeriesName or -S/--SeasonNumber')
		elif response == '"album_name" is set but not "artist_name"':
			parser.error('-d/--AlbumName is set but not -A/--ArtistName')
		elif response == '"track_name" is set but not "artist_name" or "album_name"':
			parser.error('-T/--TrackName is set but not -A/--ArtistName or -d/--AlbumName')
		else:
			parser.error(response)
	