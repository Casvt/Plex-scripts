#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Export plex metadata to a database file that can then be read from to import the data back (on a different plex instance)
	The following is supported:
		metadata, advanced metadata, watched status, posters, backgrounds (arts), collections, intro markers, chapter thumbnails and server settings
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script.
Notes:
	1. Under the following situations, it is REQUIRED that the script is run on the target server and that the script is run using the root user (administrative user):
		1. "intro_marker" when importing
		2. "chapter_thumbnail" when importing
	2. Importing chapter thumbnails on a non-linux system is not possible.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

#ADVANCED SETTINGS
#Hardcode the folder where the plex database is in
#Leave empty unless really needed
database_folder = ''
plex_linux_user = 'plex'
plex_linux_group = 'plex'

from sys import platform
from os import getenv, path, listdir
from sqlite3 import connect
from datetime import datetime
from time import perf_counter
linux_platform = platform == 'linux'
if linux_platform == True:
	from pwd import getpwnam
	from grp import getgrnam
	from os import chmod, chown, makedirs

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
database_folder = getenv('database_folder', database_folder)
base_url = f"http://{plex_ip}:{plex_port}"
request_cache = {}
if linux_platform == True:
	plex_linux_user = getenv('plex_linux_user', plex_linux_user)
	plex_linux_group = getenv('plex_linux_group', plex_linux_group)
	plex_linux_user = getpwnam(plex_linux_user).pw_uid
	plex_linux_group = getgrnam(plex_linux_group).gr_gid

#media types tuple content: metadata keys, plex type id, table creation command, plex children type id, plex children types
media_types = {
	'movie': (
		(
			'title', 'titleSort', 'originalTitle',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio', 'tagline', 'summary',
			'Genre', 'Writer', 'Director'
		),
		1,
		"""
		CREATE TABLE IF NOT EXISTS movie (
			rating_key VARCHAR(15) PRIMARY KEY,
			guid VARCHAR(120),
			updated_at INTEGER(8),
			title VARCHAR(255),
			titleSort VARCHAR(255),
			originalTitle VARCHAR(255),
			originallyAvailableAt VARCHAR(10),
			contentRating VARCHAR(15),
			userRating FLOAT,
			studio VARCHAR(255),
			tagline VARCHAR(255),
			summary TEXT,
			Genre TEXT,
			Writer TEXT,
			Director TEXT,
			languageOverride VARCHAR(5),
			useOriginalTitle INTEGER(1),
			watched_status TEXT,
			hash VARCHAR(255),
			chapter_thumbnails BLOB,
			poster BLOB,
			art BLOB
		);
		""",
		1,
		['movie']
	),
	'show': (
		(
			'title', 'titleSort', 'originalTitle',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio', 'tagline', 'summary',
			'Genre'
		),
		2,
		"""
		CREATE TABLE IF NOT EXISTS show (
			rating_key VARCHAR(15) PRIMARY KEY,
			guid VARCHAR(120),
			updated_at INTEGER(8),
			title VARCHAR(255),
			titleSort VARCHAR(255),
			originalTitle VARCHAR(255),
			originallyAvailableAt VARCHAR(10),
			contentRating VARCHAR(15),
			userRating FLOAT,
			studio VARCHAR(255),
			tagline VARCHAR(255),
			summary TEXT,
			Genre TEXT,
			episodeSort INTEGER(1),
			autoDeletionItemPolicyUnwatchedLibrary INTEGER(2),
			autoDeletionItemPolicyWatchedLibrary INTEGER(3),
			flattenSeasons INTEGER(1),
			showOrdering VARCHAR(10),
			languageOverride VARCHAR(5),
			useOriginalTitle INTEGER(1),
			poster BLOB,
			art BLOB
		);
		""",
		4,
		['show','season','episode']
	),
	'season': (
		(
			'title', 'summary'
		),
		3,
		"""
		CREATE TABLE IF NOT EXISTS season (
			rating_key VARCHAR(15) PRIMARY KEY,
			guid VARCHAR(120),
			updated_at INTEGER(8),
			title VARCHAR(255),
			summary TEXT,
			poster BLOB,
			art BLOB
		);
		""",
		4,
		['season','episode']
	),
	'episode': (
		(
			'title', 'titleSort',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'summary',
			'Writer', 'Director'
		),
		4,
		"""
		CREATE TABLE IF NOT EXISTS episode (
			rating_key VARCHAR(15) PRIMARY KEY,
			guid VARCHAR(120),
			updated_at INTEGER(8),
			title VARCHAR(255),
			titleSort VARCHAR(255),
			originallyAvailableAt VARCHAR(10),
			contentRating VARCHAR(15),
			userRating FLOAT,
			summary TEXT,
			Writer TEXT,
			Director TEXT,
			intro_start INTEGER,
			intro_end INTEGER,
			watched_status TEXT,
			hash VARCHAR(255),
			chapter_thumbnails BLOB,
			poster BLOB,
			art BLOB
		);
		""",
		4,
		['episode']
	),
	'artist': (
		(
			'title', 'titleSort', 'summary',
			'Genre', 'Style', 'Mood', 'Country', 'Similar'
		),
		8,
		"""
		CREATE TABLE IF NOT EXISTS artist (
			rating_key VARCHAR(15) PRIMARY KEY,
			guid VARCHAR(120),
			updated_at INTEGER(8),
			title VARCHAR(255),
			titleSort VARCHAR(255),
			summary TEXT,
			Genre TEXT,
			Style TEXT,
			Mood TEXT,
			Country TEXT,
			Similar TEXT,
			albumSort INTEGER(1),
			poster BLOB,
			art BLOB
		);
		""",
		10,
		['artist','album','track']
	),
	'album': (
		(
			'title', 'titleSort',
			'originallyAvailableAt', 'contentRating', 'userRating',
			'studio','summary',
			'Genre', 'Style', 'Mood'
		),
		9,
		"""
		CREATE TABLE IF NOT EXISTS album (
			rating_key VARCHAR(15) PRIMARY KEY,
			guid VARCHAR(120),
			updated_at INTEGER(8),
			title VARCHAR(255),
			titleSort VARCHAR(255),
			originallyAvailableAt VARCHAR(10),
			contentRating VARCHAR(15),
			userRating FLOAT,
			studio VARCHAR(255),
			summary TEXT,
			Genre TEXT,
			Style TEXT,
			Mood TEXT,
			poster BLOB,
			art BLOB
		);
		""",
		10,
		['album','track']
	),
	'track': (
		(
			'title', 'originalTitle',
			'contentRating', 'userRating', '[index]', 'parentIndex',
			'Mood'
		),
		10,
		"""
		CREATE TABLE IF NOT EXISTS track (
			rating_key VARCHAR(15) PRIMARY KEY,
			guid VARCHAR(120),
			updated_at INTEGER(8),
			title VARCHAR(255),
			originalTitle VARCHAR(255),
			contentRating VARCHAR(15),
			userRating FLOAT,
			[index] INTEGER,
			parentIndex INTEGER,
			Mood TEXT
		);
		""",
		10,
		['track']
	),
	'collection': (
		(
			'title', 'titleSort', 'contentRating', 'summary',
			'collectionMode', 'collectionSort',
			'subtype'
		),
		18,
		"""
		CREATE TABLE IF NOT EXISTS collection (
			rating_key VARCHAR(15) PRIMARY KEY,
			updated_at INTEGER(8),
			title VARCHAR(255),
			titleSort VARCHAR(255),
			contentRating TEXT,
			summary TEXT,
			collectionMode INTEGER(1),
			collectionSort INTEGER(1),
			subtype VARCHAR(10),
			guids TEXT,
			poster BLOB,
			art BLOB
		);
		""",
		18,
		['collection']
	),
	'server': (
		(
			'FriendlyName','sendCrashReports','PushNotificationsEnabled','logDebug','LogVerbose','ButlerUpdateChannel',
			'ManualPortMappingMode', 'ManualPortMappingPort', 'WanTotalMaxUploadRate', 'WanPerStreamMaxUploadRate',
			'FSEventLibraryUpdatesEnabled', 'FSEventLibraryPartialScanEnabled', 'watchMusicSections', 'ScheduledLibraryUpdatesEnabled', 'ScheduledLibraryUpdateInterval', 'autoEmptyTrash', 'allowMediaDeletion', 'OnDeckWindow', 'OnDeckLimit', 'OnDeckIncludePremieres', 'SmartShuffleMusic', 'MusicSeparateAlbumTypes', 'ScannerLowPriority', 'GenerateBIFBehavior', 'GenerateIntroMarkerBehavior', 'GenerateChapterThumbBehavior', 'LoudnessAnalysisBehavior', 'MusicAnalysisBehavior', 'LocationVisibility',
			'EnableIPv6', 'secureConnections', 'customCertificatePath', 'customCertificateKey', 'customCertificateDomain', 'PreferredNetworkInterface', 'DisableTLSv1_0', 'GdmEnabled', 'WanPerUserStreamCount', 'LanNetworksBandwidth', 'MinutesAllowedPaused', 'TreatWanIpAsLocal', 'RelayEnabled', 'customConnections', 'allowedNetworks', 'WebHooksEnabled',
			'TranscoderQuality', 'TranscoderTempDirectory', 'TranscoderThrottleBuffer', 'TranscoderH264BackgroundPreset', 'TranscoderToneMapping', 'TranscoderCanOnlyRemuxVideo', 'HardwareAcceleratedCodecs', 'HardwareAcceleratedEncoders', 'TranscodeCountLimit',
			'DlnaEnabled', 'DlnaClientPreferences', 'DlnaReportTimeline', 'DlnaDefaultProtocolInfo', 'DlnaDeviceDiscoveryInterval', 'DlnaAnnouncementLeaseTime', 'DlnaDescriptionIcons',
			'ButlerStartHour', 'ButlerEndHour', 'ButlerTaskBackupDatabase', 'ButlerDatabaseBackupPath', 'ButlerTaskOptimizeDatabase', 'ButlerTaskCleanOldBundles', 'ButlerTaskCleanOldCacheFiles', 'ButlerTaskRefreshLocalMedia', 'ButlerTaskRefreshLibraries', 'ButlerTaskUpgradeMediaAnalysis', 'ButlerTaskRefreshPeriodicMetadata', 'ButlerTaskDeepMediaAnalysis', 'ButlerTaskReverseGeocode', 'ButlerTaskGenerateAutoTags',
			'CinemaTrailersType', 'CinemaTrailersFromLibrary', 'CinemaTrailersFromTheater', 'CinemaTrailersFromBluRay', 'CinemaTrailersPrerollID', 'GlobalMusicVideoPath'
		),
		-1,
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
		-1,
		[]
	)
}
process_summary = {
	'metadata': "The standard plex metadata like title, summary, tags and more.",
	'advanced_metadata': "The advanced plex settings (metadata) for media",
	'watched_status': "The watched status of the media for every user: watched, not watched or partially watched.",
	'poster': "The (custom) poster of movies, shows, seasons, artists and albums.",
	'episode_poster': "The (custom) poster of episodes.",
	'art': "The (custom) art of movies, shows, seasons, artists and albums.",
	'episode_art': "The (custom) art of episodes.",
	'collection': "The collections in every library",
	'intro_marker': "The intro marker of episodes, which describes the beginning and end of the intro.",
	'chapter_thumbnail': "The by plex automatically generated thumbnails for chapters.",
	'server_settings': "The settings of the server"
}
process_types = ('import','export','reset')
advanced_metadata_keys = ('languageOverride','useOriginalTitle','episodeSort','autoDeletionItemPolicyUnwatchedLibrary','autoDeletionItemPolicyWatchedLibrary','flattenSeasons','showOrdering','albumSort')
advanced_collection_keys = ('collectionMode','collectionSort')
metadata_skip_keys = ('rating_key','guid','updated_at','poster','art','watched_status','intro_start','intro_end','hash','subtype','guids') + advanced_metadata_keys + advanced_collection_keys + media_types['server'][0]

def _leave(db, plex_db=None, e=None):
	#called upon early exit of script
	print('Shutting down...')
	db.commit()
	if plex_db != None:
		plex_db.commit()
	print('Progress saved')
	if e != None:
		print('AN ERROR OCCURED. ALL YOUR PROGRESS IS SAVED. PLEASE SHARE THE FOLLOWING WITH THE DEVELOPER:')
		raise e
	exit(0)

def _req_cache(ssn, url, params={}, headers={}):
	#use for general requests in the hope that it is requested multiple times
	#and that way the cached result from the first time is returned
	global request_cache

	if not url in request_cache:
		request_cache[url] = ssn.get(url, params=params, headers=headers).json()

	return request_cache[url]

def _export(
		type: str, data: dict, ssn, cursor, user_data: tuple, watched_map: dict, timestamp_map: dict,
		target_metadata: bool, target_advanced_metadata: bool, target_watched: bool, target_intro_markers: bool, target_chapter_thumbnail: bool,
		target_poster: bool, target_episode_poster: bool, target_art: bool, target_episode_art: bool,
		database_folder=None, hash_map=None
	):
	user_ids, user_tokens = user_data

	#extract different data based on the type
	if type in media_types:
		keys = media_types[type][0]
	else:
		#unknown type of source
		return 'Unknown source type when trying to extract data (internal error)'

	#if requested, export server settings here and return function (server settings is a "special" case)
	if type == 'server':
		machine_id = _req_cache(ssn, f"{base_url}/")['MediaContainer']['machineIdentifier']
		cursor.execute(f"DELETE FROM {type} WHERE machine_id = ?", (machine_id,))
		db_keys, db_values = ['machine_id'], [machine_id]
		prefs = _req_cache(ssn, f'{base_url}/:/prefs')['MediaContainer']['Setting']
		for pref in prefs:
			if not pref['id'] in media_types['server'][0]: continue
			db_keys.append(pref['id'])
			db_values.append(pref['value'])
		#write to the database
		comm = f"""
		INSERT INTO {type} ({",".join(db_keys)})
		VALUES ({",".join(['?'] * len(db_keys))})
		"""
		cursor.execute(comm, db_values)
		return

	rating_key = data['ratingKey']

	#skip media if it hasn't been edited since last time (or it isn't matched to any series)
	updated_at = timestamp_map[type].get(rating_key)
	if updated_at != None:
		if updated_at == data.get('updatedAt',0):
			return
		else:
			cursor.execute(f"DELETE FROM {type} WHERE rating_key = '{rating_key}'")
	elif type == 'collection':
		#collection either hasn't been added to db yet or has been imported after exporting
		cursor.execute(f'DELETE FROM {type} WHERE title = "{data["title"]}";')

	#if requested, export collection here and return function (collection is a "special" case)
	if type == 'collection':
		if data.get('smart') == '1': return
		#export metadata
		collection_info = ssn.get(f'{base_url}/library/collections/{data["ratingKey"]}', params={'includePreferences': '1'}).json()['MediaContainer']['Metadata'][0]
		db_keys, db_values = ['rating_key','updated_at'], [rating_key, collection_info.get('updatedAt',0)]
		for key in keys:
			if key == 'titleSort':
				value = collection_info.get('titleSort', collection_info.get('title', ''))
			else:
				value = collection_info.get(key)

			if value != None:
				db_keys.append(key)
				db_values.append(value)

		#export preferences
		db_keys += [s['id'] for s in collection_info['Preferences']['Setting']]
		db_values += [s['value'] for s in collection_info['Preferences']['Setting']]

		#export entries
		collection_content = ssn.get(f'{base_url}/library/collections/{data["ratingKey"]}/children', params={'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])
		db_keys.append('guids')
		db_values.append("|".join([str(m['Guid']) for m in collection_content if 'Guid' in m]))

		#export images
		if 'thumb' in collection_info:
			r = ssn.get(f'{base_url}{collection_info["thumb"]}')
			if r.status_code == 200:
				db_keys.append('poster')
				db_values.append(r.content)

		if 'art' in collection_info:
			r = ssn.get(f'{base_url}{collection_info["art"]}')
			if r.status_code == 200:
				db_keys.append('art')
				db_values.append(r.content)

		#write to database
		comm = f"""
		INSERT INTO {type} ({",".join(db_keys)})
		VALUES ({",".join(['?'] * len(db_keys))})
		"""
		cursor.execute(comm, db_values)
		return

	if not 'Guid' in data: return

	#request certain media again when we need it's metadata (lib output doesn't show all)
	if (target_metadata == True and type != 'season') \
	or (target_intro_markers == True and type == 'episode') \
	or (target_chapter_thumbnail == True and type in ('movie','episode')) \
	or (target_advanced_metadata == True and type == 'movie'):
		media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}', params={'includeGuids': '1', 'includeMarkers': '1', 'includeChapters': '1', 'includePreferences': '1'})
		if media_info.status_code != 200: return
		media_info = media_info.json()['MediaContainer']['Metadata'][0]
	else:
		media_info = data

	#extract data and built up key-value pair for db
	db_keys = ['rating_key','guid','updated_at']
	db_values = [rating_key,str(media_info['Guid']),media_info.get('updatedAt',0)]
	if target_metadata == True:
		for key in keys:
			if key[0].isupper():
				value = ",".join([x['tag'] for x in media_info.get(key, [])]) or None
			elif key == '[index]':
				value = media_info.get('index')
			elif key == 'titleSort' and type != 'track':
				value = media_info.get('titleSort', media_info.get('title', ''))
			else:
				value = media_info.get(key)

			if value != None:
				db_keys.append(key)
				db_values.append(value)

	if target_advanced_metadata == True and type in ('movie','show','artist'):
		db_keys += [s['id'] for s in media_info['Preferences']['Setting']]
		db_values += [s['value'] for s in media_info['Preferences']['Setting']]

	if target_watched == True and type in ('movie','episode'):
		db_keys.append('watched_status')
		db_watched = ['_admin',str(media_info.get('viewOffset', 'viewCount' in media_info))]
		for user_id, user_token in zip(user_ids, user_tokens):
			user_watched = str(watched_map.get(user_token, {}).get(rating_key, ''))
			if user_watched == '': continue
			db_watched += [user_id, user_watched]
		db_values.append(",".join(db_watched))

	if target_intro_markers == True and type in 'episode':
		for marker in media_info.get('Marker',[]):
			if marker['type'] == 'intro':
				#intro marker found
				db_keys += ['intro_start','intro_end']
				db_values += [marker['startTimeOffset'], marker['endTimeOffset']]
				break

	if target_chapter_thumbnail == True and type in ('movie','episode'):
		hash = hash_map[rating_key]
		bundle = path.join(path.dirname(path.dirname(database_folder)), 'Media', 'localhost', hash[0], f'{hash[1:]}.bundle', 'Contents', 'Chapters')
		# #check if media doesn't already have autogenerated thumbs and if hash matches
		if path.isdir(bundle):
			db_keys += ['hash','chapter_thumbnails']
			db_values.append(hash)
			db_values.append((b'\0' * 20).join(map(lambda c: open(path.join(bundle, c), 'rb').read(), listdir(bundle))))

	if (target_poster == True and not type in ('episode','track')) or (target_episode_poster == True and type == 'episode'):
		if 'thumb' in media_info:
			r = ssn.get(f'{base_url}{media_info["thumb"]}')
			if r.status_code == 200:
				db_keys.append('poster')
				db_values.append(r.content)

	if (target_art == True and not type in ('episode','track')) or (target_episode_art == True and type == 'episode'):
		if 'art' in media_info:
			r = ssn.get(f'{base_url}{media_info["art"]}')
			if r.status_code == 200:
				db_keys.append('art')
				db_values.append(r.content)

	#write to the database
	comm = f"""
	INSERT INTO {type} ({",".join(db_keys)})
	VALUES ({",".join(['?'] * len(db_keys))})
	"""
	cursor.execute(comm, db_values)

	return

def _import(
		type: str, data: dict, ssn, cursor, media_lib_id: str, user_data: tuple, watched_map: dict, timestamp_map: dict,
		target_metadata: bool, target_advanced_metadata: bool, target_watched: bool, target_intro_markers: bool, target_chapter_thumbnail: bool,
		target_poster: bool, target_episode_poster: bool, target_art: bool, target_episode_art: bool,
		plex_cursor=None, database_folder=None, hash_map=None
	):
	user_ids, user_tokens = user_data

	#import different data based on the type
	if type in media_types:
		media_type = media_types[type][1]
	else:
		return 'Unknown source type when trying to import data (internal error)'

	if type in ('server','collection'):
		machine_id = _req_cache(ssn, f"{base_url}/")['MediaContainer']['machineIdentifier']

	if type == 'server':
		cursor.execute(f"SELECT * FROM {type} WHERE machine_id = ?", (machine_id,))
		server_settings = cursor.fetchone()
		if server_settings == None: return
		payload = dict(zip(media_types[type][0], server_settings[1:]))
		ssn.put(f'{base_url}/:/prefs', params=payload)
		return

	if type == 'collection':
		cursor.execute(f"SELECT * FROM {type};")
		collections = cursor.fetchall()
		collection_types = set([c[8] for c in collections])
		target_keys = next(zip(*cursor.description))
		sections = _req_cache(ssn, f'{base_url}/library/sections')['MediaContainer'].get('Directory',[])
		#go through every library and check if a collection "fits" in it
		for lib in sections:
			if not lib['type'] in collection_types: continue
			lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'type': media_types[lib['type']][3], 'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])
			#guid -> ratingkey
			lib_content = dict(map(lambda m: (str(m['Guid']), m['ratingKey']), lib_output))
			collection_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/collections').json()['MediaContainer'].get('Metadata',[])
			#title -> ratingkey
			collection_content = dict(map(lambda c: (c['title'], c['ratingKey']), collection_output))
			#go through every collection to check if it fits in library
			for collection in collections[:18]:
				collection_entries = collection[9].split("|")
				collection_keys = [lib_content.get(str(e)) for e in collection_entries]
				if len(collection_keys) == len(collection_entries):
					#collection can go in library
					#remove existing collection if present
					old_ratingkey = collection_content.get(collection[2])
					if old_ratingkey != None:
						ssn.delete(f'{base_url}/library/collections/{old_ratingkey}')
					#create collection
					new_ratingkey = ssn.post(f'{base_url}/library/collections', params={'title': collection[2], 'smart': '0', 'sectionId': lib['key'], 'type': media_types[lib['type']][3], 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(collection_keys)}'}).json()['MediaContainer']['Metadata'][0]['ratingKey']
					#set poster
					if collection[10] != None:
						ssn.post(f'{base_url}/library/collections/{new_ratingkey}/posters', data=collection[10])
					#set art
					if collection[11] != None:
						ssn.post(f'{base_url}/library/collections/{new_ratingkey}/arts', data=collection[11])
					#set settings
					payload = {
						'type': media_type,
						'id': new_ratingkey,
					}
					for option, value in zip(target_keys, collection):
						if option in metadata_skip_keys: continue
						payload[f'{option}.value'] = value or ''
						payload[f'{option}.locked'] = 1
					ssn.put(f'{base_url}/library/sections/{lib["key"]}/all', params=payload)
					#set advanced settings
					payload = {o: v for o, v in zip(target_keys, collection) if o in advanced_collection_keys}
					ssn.put(f'{base_url}/library/metadata/{new_ratingkey}/prefs', params=payload)
		return

	rating_key = data['ratingKey']
	if not 'Guid' in data: return

	#request certain media again when we need it's metadata (lib output doesn't show all)
	if target_metadata == True and type != 'season':
		media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}', params={'includeGuids': '1', 'includeMarkers': '1'})
		if media_info.status_code != 200: return
		media_info = media_info.json()['MediaContainer']['Metadata'][0]
	else:
		media_info = data

	#find media in database
	guid = str(media_info['Guid'])
	cursor.execute(f"SELECT * FROM {type} WHERE guid = ?", (guid,))
	target = cursor.fetchone()
	if target == None: return
	target_keys = next(zip(*cursor.description))

	#import data
	if target_metadata == True:
		payload = {
			'type': media_type,
			'id': rating_key,
			'thumb.locked': 1,
			'art.locked': 1
		}
		if type == 'album':
			payload['artist.id.value'] = data['parentRatingKey']

		#build the payload that sets all the values
		for option, value in zip(target_keys, target):
			if option in metadata_skip_keys: continue
			elif option[0].isupper():
				#list of labels
				value = value or ''
				value = value.split(",")
				lower_option = option.lower()
				#add tags
				for offset, list_item in enumerate(value):
					payload[f'{lower_option}[{offset}].tag.tag'] = list_item
				#remove other tags
				if option in media_info:
					payload[f'{lower_option}[].tag.tag-'] = ",".join(map(lambda x: x['tag'], media_info[option]))
				payload[f'{lower_option}.locked'] = 1
			else:
				#normal key value pair
				payload[f'{option}.value'] = value or ''
				payload[f'{option}.locked'] = 1

		#upload to plex
		ssn.put(f'{base_url}/library/sections/{media_lib_id}/all', params=payload)

	if target_advanced_metadata == True and type in ('movie','show','artist'):
		payload = {o: v for o, v in zip(target_keys, target) if o in advanced_metadata_keys}
		ssn.put(f'{base_url}/library/metadata/{rating_key}/prefs', params=payload)

	if 'poster' in target_keys and ((type != 'episode' and target_poster == True) or (type == 'episode' and target_episode_poster == True)):
		ssn.post(f'{base_url}/library/metadata/{rating_key}/posters', data=target[target_keys.index('poster')])

	if 'art' in target_keys and ((type != 'episode' and target_art == True) or (type == 'episode' and target_episode_art == True)):
		ssn.post(f'{base_url}/library/metadata/{rating_key}/arts', data=target[target_keys.index('art')])

	if 'watched_status' in target_keys and target_watched == True:
		watched_info = target[target_keys.index('watched_status')].split(',')
		for user, watched_state in zip(watched_info[::2], watched_info[1::2]):
			if user == '_admin': user_token = plex_api_token
			else: user_token = user_tokens[user_ids.index(user)]

			#set watched status of media for this user
			if watched_state == 'True':
				#mark watched
				ssn.get(f'{base_url}/:/scrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key, 'X-Plex-Token': user_token})
			elif watched_state == 'False':
				#mark not-watched
				ssn.get(f'{base_url}/:/unscrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key, 'X-Plex-Token': user_token})
			elif watched_state.isdigit():
				#mark partially watched
				ssn.get(f'{base_url}/:/progress', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key, 'time': watched_state, 'state': 'stopped', 'X-Plex-Token': user_token})

	if 'intro_start' in target_keys and 'intro_end' in target_keys and target_intro_markers == True:
		#check if media already has intro marker
		plex_cursor.execute("SELECT * FROM taggings WHERE text = 'intro' AND metadata_item_id = ?;", (rating_key,))
		if plex_cursor.fetchone() == None:
			#no intro marker exists so create one
			d = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			plex_cursor.execute("SELECT tag_id FROM taggings WHERE text = 'intro';")
			i = plex_cursor.fetchone()
			if i == None:
				#no id yet for intro's so make one that isn't taken yet
				plex_cursor.execute("SELECT tag_id FROM taggings ORDER BY tag_id DESC;")
				i = int(plex_cursor.fetchone()[0]) + 1
			else:
				i = i[0]
			plex_cursor.execute(f"""
				INSERT INTO taggings (
					metadata_item_id,
					tag_id,
					[index],
					text,
					time_offset,
					end_time_offset,
					thumb_url,
					created_at,
					extra_data
				) VALUES (?, ?, 0, 'intro', ?, ?, '', ?, 'pv%3Aversion=5');
			""", (rating_key, i, target[target_keys.index('intro_start')], target[target_keys.index('intro_end')], d))
		else:
			#intro marker exists so update timestamps
			plex_cursor.execute("""
				UPDATE taggings
				SET
					time_offset = ?,
					end_time_offset = ?
				WHERE
					text = 'intro'
					AND metadata_item_id = ?;
			""", (target[target_keys.index('intro_start')], target[target_keys.index('intro_end')], rating_key))

	if 'hash' in target_keys and 'chapter_thumbnails' in target_keys and target_chapter_thumbnail == True:
		hash = hash_map[rating_key]
		bundle = path.join(path.dirname(path.dirname(database_folder)), 'Media', 'localhost', hash[0], f'{hash[1:]}.bundle', 'Contents', 'Chapters')
		#check if media doesn't already have autogenerated thumbs and if hash matches
		if target[target_keys.index('hash')] == hash and not path.isdir(bundle):
			thumbs = target[target_keys.index('chapter_thumbnails')].split(b'\0' * 20)
			#create folder path to put thumbs in
			bundle = path.dirname(path.dirname(database_folder))
			for folder in ('Media', 'localhost', hash[0], f'{hash[1:]}.bundle', 'Contents', 'Chapters'):
				bundle = path.join(bundle, folder)
				makedirs(bundle)
				chmod(bundle, 0o755)
				chown(bundle, plex_linux_user, plex_linux_group)

			#put all thumbs in created folder
			for index, thumb in enumerate(thumbs):
				chapter_file = path.join(bundle, f'chapter{index+1}.jpg')
				with open(chapter_file, 'wb') as f:
					f.write(thumb)
				chmod(chapter_file, 0o644)
				chown(bundle, plex_linux_user, plex_linux_group)
	return

def _reset(
		type: str, data: dict, ssn, cursor, media_lib_id: str, watched_map: dict, timestamp_map: dict,
		target_metadata: bool, target_poster: bool, target_art: bool
	):
	#reset different data based on the type
	if type in media_types:
		keys, media_type = media_types[type][:2]
	else:
		return 'Unknown source type when trying to reset data (internal error)'

	#set all fields to unlocked in plex
	rating_key = data['ratingKey']
	payload = {
		'type': media_type,
		'id': rating_key
	}
	if type == 'collection':
		for key in keys:
			if key in metadata_skip_keys: continue
			payload[f'{key}.locked'] = 0
	else:
		if target_poster == True:
			payload['thumb.locked'] = 0
		if target_art == True:
			payload['art.locked'] = 0
		if target_metadata == True:
			for key in keys:
				if key[0].isupper():
					payload[f'{key.lower()}.locked'] = 0
				else:
					payload[f'{key}.locked'] = 0

	ssn.put(f'{base_url}/library/sections/{media_lib_id}/all', params=payload)

	return

def plex_exporter_importer(
		verbose: bool, ssn, type: str, process: list, location: str,
		all: bool, all_movie: bool=False, all_show: bool=False, all_music: bool=False,
		library_name: str=None,
		movie_name: str=None,
		series_name: str=None, season_number: int=None, episode_number: int=None,
		artist_name: str=None, album_name: str=None, track_name: str=None
	):
	result_json, watched_map, timestamp_map = [], {}, {}
	lib_target_specifiers = (library_name,movie_name,series_name,season_number,episode_number,artist_name,album_name,track_name)
	all_target_specifiers = (all_movie, all_show, all_music)

	#check for illegal arg parsing
	if not type in process_types:
		return 'Invalid value for "type"'
	if platform == False and type == 'import' and 'chapter_thumbnails' in process:
		return 'Importing chapter thumbnails on a non-linux system is not supported'
	#setup db location
	if type == 'export':
		if path.isdir(location):
			database_file = f'{path.splitext(path.abspath(__file__))[0]}.db'
			if path.isfile(database_file):
				print(f'Exporting to {database_file} (Updating)')
			else:
				print(f'Exporting to {database_file}')

		elif location.endswith('.db'):
			database_file = location
			if path.isfile(location):
				print(f'Exporting to {database_file} (Updating)')
			else:
				print(f'Exporting to {database_file}')

		else:
			return 'Location not found'

	elif type == 'import':
		if path.isfile(location):
			database_file = location
			print(f'Importing from {database_file}')
		else:
			return 'Location not found'

	elif type == 'reset':
		if path.isdir(location):
			database_file = f'{path.splitext(path.abspath(__file__))[0]}.db'
		elif path.isfile(location):
			if not location.endswith('.db'):
				return 'Invalid location value; file needs to have ".db" extension'
			database_file = location
		else:
			return 'Location not found'

	#build summary
	#what's going to be processed
	summary = f"You're going to {type} the following:\n"
	summary += ''.join([f'	{process_summary.get(process_entry, process_entry)}\n' for process_entry in process])
	#what's targeted
	summary += f'This is going to be done for '
	if 'server_settings' in process or 'collection' in process:
		summary += 'your server'
		if len(process) > 1:
			summary += ' and '
	if all == True: summary += 'your complete plex library'
	elif True in (all_movie, all_show, all_music):
		targeted_libs = []
		if all_movie == True: targeted_libs.append('movie')
		if all_show == True: targeted_libs.append('show')
		if all_music == True: targeted_libs.append('music')
		summary += f'all {"/".join(targeted_libs)} libraries'
	else:
		if movie_name != None: summary += f'{library_name} -> {movie_name}'
		elif series_name != None:
			summary += f'{library_name} -> {series_name}'
			if season_number != None:
				summary += f' -> Season {season_number}'
				if episode_number != None: summary += f' -> Episode {episode_number}'
		elif artist_name != None:
			summary += f'{library_name} -> {artist_name}'
			if album_name != None:
				summary += f' -> Album {album_name}'
				if track_name != None: summary += f' -> Track {track_name}'
		elif not (len(process) == 1 and process[0] in ('server_settings','collection')): summary += f'the library {library_name}'
	summary += '.\n'
	print(summary)

	#setup connection to plex db if needed
	if ('intro_marker' in process and type == 'import') or ('chapter_thumbnail' in process and type in ('import','export')):
		#importing intro markers or chapter thumbnails requires root and access to target plex database file
		from os import geteuid
		if (type == 'import' and any(k in process for k in ('intro_marker','chapter_thumbnail'))) and geteuid() != 0:
			return 'Intro Marker- or Chapter Thumbnail importing or Chapter Thumbnail exporting is requested but script is not run as root'

		#get location to database file
		database_root = database_folder or dict(map(lambda d: (d['id'], d['value']), _req_cache(ssn, f'{base_url}/:/prefs')['MediaContainer']['Setting']))['ButlerDatabaseBackupPath']
		db_file = path.join(database_root, 'com.plexapp.plugins.library.db')
		if not path.isfile(db_file):
			return 'Intro Marker- or Chapter Thumbnail importing or Chapter Thumbnail exporting is requested but script is not run on target plex server, or value of database_folder is invalid'

		#setup db connection
		plex_db = connect(db_file)
		plex_cursor = plex_db.cursor()

		#create hash_map if needed
		if 'chapter_thumbnail' in process:
			plex_cursor.execute("SELECT id, hash FROM metadata_items;")
			hash_map = dict(map(lambda i: (str(i[0]), i[1]), plex_cursor.fetchall()))

	#check for illegal arg parsing
	if all == True:
		if lib_target_specifiers.count(None) < len(lib_target_specifiers) or True in all_target_specifiers:
			return 'Both "all" and a target-specifier are set'

	else:
		if not True in all_target_specifiers and library_name == None and not (len(process) == 1 and process[0] in ('server_settings','collection')):
			return '"all" is set to False but no target-specifier is given'
		if season_number != None and series_name == None:
			return '"season_number" is set but not "series_name"'
		if episode_number != None and (season_number == None or series_name == None):
			return '"episode_number" is set but not "season_number" or "series_name"'
		if album_name != None and artist_name == None:
			return '"album_name" is set but not "artist_name"'
		if track_name != None and (album_name == None or artist_name == None):
			return '"track_name" is set but not "album_name" or "artist_name"'

	#setup variables
	db = connect(database_file)
	cursor = db.cursor()
	#create tables
	cursor.executescript(''.join(media_type[2] for media_type in media_types.values()))

	machine_id = _req_cache(ssn, f'{base_url}/')['MediaContainer']['machineIdentifier']
	shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers').text
	result = map(lambda r: r.split('"')[0:3:2], shared_users.split('userID="')[1:])
	user_data = tuple(zip(*result))
	if type == 'export':
		method = _export
	elif type == 'import':
		method = _import
	elif type == 'reset':
		method = _reset
	args = {
		'ssn': ssn,
		'cursor': cursor,
		'target_poster': 'poster' in process,
		'target_art': 'art' in process,
		'target_metadata': 'metadata' in process
	}
	exit_args = {
		'db': db
	}
	if type in ('export','import'):
		args['user_data'] = user_data
		args['target_advanced_metadata'] = 'advanced_metadata' in process
		args['target_episode_poster'] = 'episode_poster' in process
		args['target_episode_art'] = 'episode_art' in process
		args['target_watched'] = 'watched_status' in process
		args['target_intro_markers'] = 'intro_marker' in process
		args['target_chapter_thumbnail'] = 'chapter_thumbnail' in process
		if 'chapter_thumbnail' in process:
			args['hash_map'] = hash_map
			args['database_folder'] = database_root
	if type == 'import' and any(p in process for p in ('intro_marker','chapter_thumbnail')):
		args['plex_cursor'] = plex_cursor
		exit_args['plex_db'] = plex_db

	#start working on the media/settings
	try:
		if 'server_settings' in process:
			print('Server Settings')
			if type == 'import':
				response = method(type='server', data={}, watched_map=watched_map, timestamp_map=timestamp_map, media_lib_id=0, **args)
			else:
				response = method(type='server', data={}, watched_map=watched_map, timestamp_map=timestamp_map, **args)
			if isinstance(response, str): return response

		sections = _req_cache(ssn, f'{base_url}/library/sections')['MediaContainer'].get('Directory',[])
		if 'collection' in process:
			print('Collections')
			if type in ('export','reset'):
				if type == 'export':
					cursor.execute(f"SELECT rating_key, updated_at FROM 'collection';")
					timestamp_map['collection'] = dict(cursor.fetchall())
				for lib in sections:
					collections = ssn.get(f'{base_url}/library/sections/{lib["key"]}/collections').json()['MediaContainer'].get('Metadata',[])
					for collection in collections:
						if type == 'export':
							response = method(type='collection', data=collection, watched_map=watched_map, timestamp_map=timestamp_map, **args)
						elif type == 'reset':
							response = method(type='collection', data=collection, watched_map=watched_map, timestamp_map=timestamp_map, media_lib_id=lib['key'], **args)
						if isinstance(response, str): return response
						else: result_json.append(collection['ratingKey'])

			elif type == 'import':
				response = method(type='collection', data={}, watched_map=watched_map, timestamp_map=timestamp_map, media_lib_id=0, **args)
				if isinstance(response, str): return response

		for lib in sections:
			if not (lib['type'] in media_types and (all == True \
			or (library_name != None and lib['title'] == library_name) \
			or (all_movie == True and lib['type'] == 'movie') \
			or (all_show == True and lib['type'] == 'show') \
			or (all_music == True and lib['type'] == 'artist'))):
				#a specific library is targeted and this one is not it, so skip
				continue

			#this library (or something in it) should be processed
			print(lib['title'])
			if type in ('import','reset'):
				args['media_lib_id'] = lib['key']
			lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'includeGuids': '1'})
			if lib_output.status_code != 200: continue
			lib_output = lib_output.json()['MediaContainer'].get('Metadata',[])

			if lib['type'] in ('movie','show') and type == 'export' and 'watched_status' in process:
				#create watched map for every user to reduce requests
				for user_token in user_data[1]:
					user_lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'X-Plex-Token': user_token, 'type': media_types[lib['type']][3]})
					if user_lib_output.status_code != 200: continue
					user_lib_output = user_lib_output.json()['MediaContainer'].get('Metadata', [])
					watched_map[user_token] = dict(map(lambda m: (m['ratingKey'], m.get('viewOffset','viewCount' in m)), user_lib_output))

			if type == 'export' and not lib['type'] in timestamp_map:
				#create timestamp map
				lib_types = media_types[lib['type']][4]
				for lib_type in lib_types:
					cursor.execute(f"SELECT rating_key, updated_at FROM {lib_type};")
					timestamp_map[lib_type] = dict(cursor.fetchall())

			if lib['type'] == 'movie':
				for movie in lib_output:
					if movie_name != None and movie['title'] != movie_name:
						continue

					if verbose == True: print(f'	{movie["title"]}')
					response = method(type='movie', data=movie, watched_map=watched_map, timestamp_map=timestamp_map, **args)
					if isinstance(response, str): return response
					else: result_json.append(movie['ratingKey'])

					if movie_name != None:
						break
				else:
					if movie_name != None:
						return 'Movie not found'

			elif lib['type'] == 'show':
				for show in lib_output:
					if series_name != None and show['title'] != series_name:
						continue

					if verbose == True: print(f'	{show["title"]}')
					#process show
					show_info = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}', params={'includePreferences': '1','includeGuids': '1'}).json()['MediaContainer']['Metadata'][0]
					response = method(type='show', data=show_info, watched_map=watched_map, timestamp_map=timestamp_map, **args)
					if isinstance(response, str): return response
					else: result_json.append(show['ratingKey'])

					#process seasons
					season_info = ssn.get(f'{base_url}{show["key"]}', params={'includeGuids': '1'})
					if season_info.status_code != 200: continue
					season_info = season_info.json()['MediaContainer']['Metadata']
					for season in season_info:
						if season_number != None and season['index'] != season_number:
							continue

						response = method(type='season', data=season, watched_map=watched_map, timestamp_map=timestamp_map, **args)
						if isinstance(response, str): return response
						else: result_json.append(season['ratingKey'])

						if season_number != None:
							break
					else:
						if season_number != None:
							return 'Season not found'

					#process episodes
					episode_info = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']
					for episode in episode_info:
						if season_number != None and episode['parentIndex'] != season_number:
							continue
						if episode_number != None and episode['index'] != episode_number:
							continue

						if verbose == True: print(f'		S{episode["parentIndex"]}E{episode["index"]} - {episode["title"]}')
						response = method(type='episode', data=episode, watched_map=watched_map, timestamp_map=timestamp_map, **args)
						if isinstance(response, str): return response
						else: result_json.append(episode['ratingKey'])

						if episode_number != None:
							break
					else:
						if episode_number != None:
							return 'Episode not found'

					if series_name != None:
						break
				else:
					if series_name != None:
						return 'Series not found'

			elif lib['type'] == 'artist':
				for artist in lib_output:
					if artist_name != None and artist['title'] != artist_name:
						continue

					if verbose == True: print(f'	{artist["title"]}')
					#process artist
					artist_info = ssn.get(f'{base_url}/library/metadata/{artist["ratingKey"]}', params={'includeGuids': '1','includePreferences': '1'}).json()['MediaContainer']['Metadata'][0]
					response = method(type='artist', data=artist_info, watched_map=watched_map, timestamp_map=timestamp_map, **args)
					if isinstance(response, str): return response
					else: result_json.append(artist['ratingKey'])

					#process albums
					album_info = ssn.get(f'{base_url}{artist["key"]}', params={'includeGuids': '1'})
					if album_info.status_code != 200: continue
					album_info = album_info.json()['MediaContainer'].get('Metadata',[])
					for album in album_info:
						if album_name != None and album['title'] != album_name:
							continue

						response = method(type='album', data=album, watched_map=watched_map, timestamp_map=timestamp_map, **args)
						if isinstance(response, str): return response
						else: result_json.append(album['ratingKey'])

						if album_name != None:
							break
					else:
						if album_name != None:
							return 'Album not found'

					#process tracks
					track_info = ssn.get(f'{base_url}/library/metadata/{artist["ratingKey"]}/allLeaves', params={'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])
					for track in track_info:
						if album_name != None and track['parentTitle'] != album_name:
							continue
						if track_name != None and track['title'] != track_name:
							continue

						if verbose == True: print(f'		D{track["parentIndex"]}T{track["index"]} - {track["title"]}')
						response = method(type='track', data=track, watched_map=watched_map, timestamp_map=timestamp_map, **args)
						if isinstance(response, str): return response
						else: result_json.append(track['ratingKey'])

						if track_name != None:
							break
					else:
						if track_name != None:
							return 'Track not found'

					if artist_name != None:
						break
				else:
					if artist_name != None:
						return 'Artist not found'

			else:
				print('	Library not supported')

			if library_name != None:
				break
		else:
			if library_name != None:
				return 'Library not found'
	except Exception as e:
		if 'has no column named' in str(e):
			_leave(**exit_args, e='Database file is too old, please delete the file and export to a new one')
		else:
			_leave(**exit_args, e=e)

	#save the database
	db.commit()
	if type == 'import' and ('intro_marker' in process or 'chapter_thumbnail' in process):
		plex_db.commit()

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser, RawDescriptionHelpFormatter

	#setup vars
	ssn = Session()
	ssn.headers.update({'Accept':'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	epilog = """-------------------
EPILOG

-p/--Process
{p}

	Notes:
	1. Under the following situations, it is REQUIRED that the script is run on the target server and that the script is run using the root user (administrative user):
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
	parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter, description='Export plex metadata to a database file that can then be read from to import the data back (on a different plex instance)', epilog=epilog)
	parser.add_argument('-t','--Type', choices=process_types, required=True, type=str, help='Either export/import plex metadata or reset import (unlock all fields)')
	parser.add_argument('-p','--Process', choices=process_summary.keys(), help='EXPORT/IMPORT ONLY: Select what to export/import; this argument can be given multiple times to select multiple things', action='append', required=True)
	parser.add_argument('-L','--Location', type=str, help='SEE EPILOG', default=path.dirname(path.abspath(__file__)))
	parser.add_argument('-v','--Verbose', help='Make script more verbose', action='store_true')

	#args regarding target selection
	#general selectors
	parser.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	parser.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	parser.add_argument('--AllShow', action='store_true', help='Target all show libraries')
	parser.add_argument('--AllMusic', action='store_true', help='Target all music libraries')
	parser.add_argument('-l','--LibraryName', type=str, help='Target a specific library based on it\'s name (movie, show and music libraries supported)')
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

	start_time = perf_counter()
	response = plex_exporter_importer(
		verbose=args.Verbose, ssn=ssn, type=args.Type, process=args.Process, location=args.Location,
		all=args.All, all_movie=args.AllMovie, all_show=args.AllShow, all_music=args.AllMusic,
		library_name=args.LibraryName,
		movie_name=args.MovieName,
		series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber,
		artist_name=args.ArtistName, album_name=args.AlbumName, track_name=args.TrackName
	)
	print(f'Time: {round(perf_counter() - start_time, 3)}s')
	if not isinstance(response, list):
		if response == 'Both "all" and a target-specifier are set':
			parser.error('Both -a/--All and a target-specifier are set')
		elif response == '"all" is set to False but no target-specifier is given':
			parser.error('-a/--All is not set but also no target-specifier is set')
		elif response == '"season_number" is set but not "series_name"':
			parser.error('-S/--SeasonNumber is set but not -s/--SeriesName')
		elif response == '"episode_number" is set but not "season_number" or "series_name"':
			parser.error('-e/--EpisodeNumber is set but not -S/--SeasonNumber or -s/--SeriesName')
		elif response == '"album_name" is set but not "artist_name"':
			parser.error('-d/--AlbumName is set but not -A/--ArtistName')
		elif response == '"track_name" is set but not "album_name" or "artist_name"':
			parser.error('-T/--TrackName is set but not -d/--AlbumName or -A/--ArtistName')
		else:
			parser.error(response)
