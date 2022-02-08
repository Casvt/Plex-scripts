#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	When a local stream is started, check if a version of the media exists with a higher resolution.
	This version can exist in the same folder, in a different library or on a different plex server (backup server).
	When one is found, switch the stream to that file.
Requirements (python3 -m pip install [requirement]):
	requests
	PlexAPI
	websocket-client
Setup:
	Fill in the variables below.
	Then run the script. As long as the script is running, it will handle streams correctly.
	Because the script is a constant running script, you should run it in the background (as a service or a cron '@reboot' job for example; depends on the os how to do this so google it).
"""

#required
plex_ip = ''
plex_port = ''
plex_api_token = ''

#choose wether to upgrade a stream when there is a higher audio channel count and/or video resolution found
process_audio = True
process_video = True
#choose if video resolution or audio channel count takes priority (e.g. a 1080p 5.1ch stream or a 4k 2.0ch stream)
process_priority = 'video' #'video' or 'audio'

#optional
backup_plex_ip = ''
backup_plex_port = ''
backup_plex_api_token = ''

#These are inclusion variables. Only streams that match these variables are influenced. These are optional
#IMPORTANT: Inclusion variables OVERRULE exclusion variables.
#Give the library sectionid's of the only libraries to upgrade >from<
in_library_source_ids = []
#Give the library sectionid's of the only libraries to upgrade >to<
in_library_target_ids = []
#Exactly the same as ex_library_target_ids but then for library sectionid's of the backup server.
#Only used/useful when the backup plex server is setup
in_library_remote_target_ids = []
#Give the rating keys of the only media to influence.
in_media_rating_keys = []
#Give resolutions to only upgrade from (e.g. upgrade nothing exept a 720p stream -> add '720p' to array)
#IMPORTANT: The following values are accepted:
#480p
#720p
#1080p
#2k
#4k
#6k
#8k
in_resolutions = []
#Give audio channels to only upgrade from (e.g. upgrade nothing exept 5.1 channel audio -> add 6 to array)
#IMPORTANT: fill in the total amount of channels (e.g. 5.1 = 6, 7.1.2 = 10, etc.)
in_channels = []
#Give client names to only upgrade audio on
audio_in_clients = []
#Give client names to only upgrade video on
video_in_clients = []

#These are exclution variables. Everything you put here will be excluded from upgrading. These are optional
#Give the library sectionid's of the libraries to not upgrade >from< (e.g. If you stream a movie that is in the "4K movies - no upgrade" library and add the library's id in the array, it will not upgrade that movie, as it is coming from a library that is excluded)
ex_library_source_ids = []
#Give the library sectionid's of the libraries to not upgrade >to< (e.g. You're streaming from Library1 and the script found a better version in Library2. If you have the id of Library2 added to the array below, it will not upgrade as that library is excluded from upgrading to)
ex_library_target_ids = []
#Exactly the same as ex_library_target_ids but then for library sectionid's of the backup server. So library sectionid's that you enter here will be ignored/avoided on the backup server
#Only used/useful when the backup plex server is setup
ex_library_remote_target_ids = []
#Give the rating keys of the media to ignore (e.g. if you stream Movie1 and added it's rating key below, it will not upgrade it)
ex_media_rating_keys = []
#Give resolutions to not upgrade from (e.g. upgrade everything unless it's a 720p stream -> add '720p' to array)
#IMPORTANT: The following values are accepted:
#480p
#720p
#1080p
#2k
#4k
#6k
#8k
ex_resolutions = []
#Give audio channels to not upgrade from (e.g. upgrade everything unless it's 5.1 channel audio -> add 6 to array)
#IMPORTANT: fill in the total amount of channels (e.g. 5.1 = 6, 7.1.2 = 10, etc.)
ex_channels = []
#Give client names to not upgrade audio on (e.g. dont upgrade if the stream is on the "Bedroom Shield" -> add "Bedroom Shield" to array)
audio_ex_clients = []
#Give client names to not upgrade video on
video_ex_clients = []

#example:
#only process the stream when it's a 720p stream that is not playing on the nvidea shield in the livingroom
# ->
#in_resolutions = ["720p"]
#ex_clients = ["Livingroom Shield"]

import requests, argparse, time, logging, json
from plexapi.server import PlexServer
#required for alert listener so checking here
import websocket

def get_channels(session):
	for media in session['Media']:
		if 'selected' in media.keys() and media['selected'] == True:
			for part in media['Part']:
				if 'selected' in part.keys() and part['selected'] == True:
					for stream in part['Stream']:
						if stream['streamType'] == 2 and 'selected' in stream.keys() and stream['selected'] == True:
							return stream['channels']
	logging.error('Could not find the current audio stream')
	return 'not-found'

def get_resolution(session, formatted=True):
	for media in session['Media']:
		if 'selected' in media.keys() and media['selected'] == True:
			res_number = int(media['videoResolution'].rstrip('k') + '000') if media['videoResolution'].endswith('k') else int(media['videoResolution'].rstrip('p'))
			if formatted == True:
				return res_number
			else:
				return media['videoResolution']
	logging.error('Could not find the current video stream')
	return 'not-found'

def audio(session, part_id, media_output=None):
	set_stream_source = ''
	set_stream_id = ''
	set_stream_count = ''
	channels = get_channels(session)
	if channels == 'not-found':
		return
	logging.debug(f'Current channel count is {channels}')
	if media_output == None:
		media_output = ssn.get(baseurl + session['key']).json()
	#check first if there's a better audio stream inside the file (often files have stereo and a surround sound stream)
	for media in session['Media']:
		if 'selected' in media.keys() and media['selected'] == True:
			media_id = media['id']
	for media in media_output['MediaContainer']['Metadata'][0]['Media']:
		if media['id'] == int(media_id):
			if media['audioChannels'] == channels:
				#max channel count stream already streaming from file; continuing to next step
				logging.debug('Audio stream is already the best inside the file; continuing')
				break
			#there is a better audio stream inside the file
			for part in media['Part']:
				if part['id'] == int(part_id):
					for stream in part['Stream']:
						if stream['streamType'] == 2 and stream['channels'] > channels:
							set_stream_source = 'file'
							set_stream_id = stream['id']
							set_stream_count = int(stream['channels'])
					break
			else:
				logging.error('File not found in media info')
			break
	else:
		logging.error('Media id not found back in media info')
		return

	#check if there's a better version inside a different file in the folder
	index = -1
	for media in media_output['MediaContainer']['Metadata'][0]['Media']:
		index += 1
		for part in media['Part']:
			#looping through every media file in the folder
			if not part['id'] == int(part_id):
				logging.debug(json.dumps(part, indent=4))
				for stream in part['Stream']:
					if stream['streamType'] == 2 and stream['channels'] > set_stream_count:
						set_stream_source = 'version'
						set_stream_id = stream['id']
						set_stream_count = int(stream['channels'])
						media_index = index

	#check if there's a better version inside a different file in a different library
	lib_id = int(session['librarySectionID'])
	media_type = session['type']
	for search_result in ssn.get(f'http://{plex_ip}:{plex_port}/search', params={'query': session['title']}).json()['MediaContainer']['Metadata']:
		if search_result['librarySectionID'] != lib_id and search_result['type'] == media_type and search_result['title'] == session['title']:
			search_output = ssn.get(f'http://{plex_ip}:{plex_port}{search_result["key"]}').json()
			if (ex_library_target_ids and search_output['MediaContainer']['Metadata'][0]['librarySectionID'] in ex_library_target_ids) \
			or (in_library_target_ids and not search_output['MediaContainer']['Metadata'][0]['librarySectionID'] in in_library_target_ids):
				continue
			index = -1
			for media in search_output['MediaContainer']['Metadata'][0]['Media']:
				index += 1
				for part in media['Part']:
					#looping through every media file in the folder
					if not part['id'] == int(part_id):
						logging.debug(json.dumps(part, indent=4))
						for stream in part['Stream']:
							if stream['streamType'] == 2 and stream['channels'] > set_stream_count:
								set_stream_source = 'library'
								set_stream_id = stream['id']
								set_stream_count = int(stream['channels'])
								media_index = index
								media_key = search_result['key']

	#check if there's a better version inside a different file on a backup server (if setup)
	if backup == True:
		for search_result in backup_ssn.get(f'http://{backup_plex_ip}:{backup_plex_port}/search', params={'query': session['title']}).json()['MediaContainer']['Metadata']:
			if search_result['type'] == media_type and search_result['title'] ==  session['title']:
				search_output = backup_ssn.get(f'http://{backup_plex_ip}:{backup_plex_port}{search_result["key"]}').json()
				if (ex_library_remote_target_ids and search_output['MediaContainer']['Metadata'][0]['librarySectionID'] in ex_library_remote_target_ids) \
				or (in_library_remote_target_ids and not search_output['MediaContainer']['Metadata'][0]['librarySectionID'] in in_library_remote_target_ids):
					continue
				index = -1
				for media in search_output['MediaContainer']['Metadata'][0]['Media']:
					index += 1
					for part in media['Part']:
						#looping through every media file in the folder
						if not part['id'] == int(part_id):
							logging.debug(json.dumps(part, indent=4))
							for stream in part['Stream']:
								if stream['streamType'] == 2 and stream['channels'] > set_stream_count:
									set_stream_source = 'backup'
									set_stream_id = stream['id']
									set_stream_count = int(stream['channels'])
									media_index = index
									media_key = search_result['key']

	#change the stream if needed
	if set_stream_source and set_stream_id and set_stream_count:
		#better stream found so change it
		client = plex.client(session['Player']['title'])
		view_offset = session['viewOffset']
		if set_stream_source == 'file':
			logging.info(f'A better audio stream has been found inside the file with {set_stream_count} channels')
			client.setAudioStream(audioStreamID=set_stream_id, mtype='video')
		elif set_stream_source == 'version':
			logging.info(f'A better audio stream has been found inside a different version of the file with {set_stream_count} channels')
			key = session['key']
			media = plex.fetchItem(key)
			client.stop(mtype='video')
			client.playMedia(media, offset=view_offset, key=key, mediaIndex=media_index)
			client.setAudioStream(audioStreamID=set_stream_id, mtype='video')
		elif set_stream_source == 'library':
			logging.info(f'A better audio stream has been found inside a file in a different library with {set_stream_count} channels')
			media = plex.fetchItem(media_key)
			client.stop(mtype='video')
			client.playMedia(media, offset=view_offset, key=media_key, mediaIndex=media_index)
			client.setAudioStream(audioStreamID=set_stream_id, mtype='video')
		elif set_stream_source == 'backup':
			logging.info(f'A better audio stream has been found inside a file on the backup server with {set_stream_count} channels')
			media = backup_plex.fetchItem(media_key)
			client.stop(mtype='video')
			backup_client = backup_plex.client(session['Player']['title'])
			backup_client.playMedia(media, offset=view_offset, key=media_key, mediaIndex=media_index)
			backup_client.setAudioStream(audioStreamID=set_stream_id, mtype='video')

def video(session, part_id, media_output=None):
	set_stream_source = ''
	set_stream_count = ''
	res = get_resolution(session)
	if res == 'not-found':
		return
	logging.debug(f'Current resolution is {res}')
	if media_output == None:
		media_output = ssn.get(baseurl + session['key']).json()
	#check if there's a better version in a different file in the folder
	index = -1
	for media in media_output['MediaContainer']['Metadata'][0]['Media']:
		index += 1
		res_number = int(media['videoResolution'].rstrip('k') + '000') if media['videoResolution'].endswith('k') else int(media['videoResolution'].rstrip('p'))
		if res_number > res:
			set_stream_source = 'version'
			set_stream_count = res_number
			media_index = index

	#check if there's a better version in a different library
	lib_id = int(session['librarySectionID'])
	media_type = session['type']
	for search_result in ssn.get(f'http://{plex_ip}:{plex_port}/search', params={'query': session['title']}).json()['MediaContainer']['Metadata']:
		if search_result['librarySectionID'] != lib_id and search_result['type'] == media_type and search_result['title'] == session['title']:
			search_output = ssn.get(f'http://{plex_ip}:{plex_port}{search_result["key"]}').json()
			index = -1
			for media in search_output['MediaContainer']['Metadata'][0]['Media']:
				index += 1
				res_number = int(media['videoResolution'].rstrip('k') + '000') if media['videoResolution'].endswith('k') else int(media['videoResolution'].rstrip('p'))
				if res_number > set_stream_count:
					set_stream_source = 'library'
					set_stream_count = res_number
					media_index = index
					media_key = search_result['key']

	#check if there's a better version inside a different file on a backup server (if setup)
	if backup == True:
		for search_result in backup_ssn.get(f'http://{backup_plex_ip}:{backup_plex_port}/search', params={'query': session['title']}).json()['MediaContainer']['Metadata']:
			if search_result['type'] == media_type and search_result['title'] ==  session['title']:
				search_output = backup_ssn.get(f'http://{backup_plex_ip}:{backup_plex_port}{search_result["key"]}').json()
				index = -1
				for media in search_output['MediaContainer']['Metadata'][0]['Media']:
					index += 1
					res_number = int(media['videoResolution'].rstrip('k') + '000') if media['videoResolution'].endswith('k') else int(media['videoResolution'].rstrip('p'))
					if res_number > set_stream_count:
						set_stream_source = 'backup'
						set_stream_count = res_number
						media_index = index
						media_key = search_result['key']

	#change the stream if needed
	if set_stream_source and set_stream_id and set_stream_count:
		#better stream found so change it
		client = plex.client(session['Player']['title'])
		view_offset = session['viewOffset']
		if set_stream_source == 'version':
			logging.info(f'A better video stream has been found inside a different version of the file with the resolution of {set_stream_count}')
			key = session['key']
			media = plex.fetchItem(key)
			client.stop(mtype='video')
			client.playMedia(media, offset=view_offset, key=key, mediaIndex=media_index)
		elif set_stream_source == 'library':
			logging.info(f'A better video stream has been found inside a file in a different library with the resolution of {set_stream_count}')
			media = plex.fetchItem(media_key)
			client.stop(mtype='video')
			client.playMedia(media, offset=view_offset, key=media_key, mediaIndex=media_index)
		elif set_stream_source == 'backup':
			logging.info(f'A better video stream has been found inside a file on the backup server with the resolution of {set_stream_count}')
			media = backup_plex.fetchItem(media_key)
			client.stop(mtype='video')
			backup_client = backup_plex.client(session['Player']['title'])
			backup_client.playMedia(media, offset=view_offset, key=media_key, mediaIndex=media_index)

def process(data):
	# logging.debug(json.dumps(data, indent=4))
	if data['type'] == 'playing' and data['PlaySessionStateNotification'][0]['viewOffset'] < 500:
		#stream has started
		logging.debug(json.dumps(data, indent=4))
		data = data['PlaySessionStateNotification'][0]
		session_key = data['sessionKey']
		sessions = ssn.get(baseurl + '/status/sessions').json()
		for session in sessions['MediaContainer']['Metadata']:
			if session['sessionKey'] == session_key:
				if session['Session']['location'] != 'lan':
					logging.info('Detected session but it isn\'t streamed locally so ignoring')
					return
				logging.info('Detected local session so handling it')
				logging.debug(json.dumps(session, indent=4))
				#session is found, starting and local; check if it is allowed to be processed
				if (in_library_source_ids and not session['librarySectionID'] in in_library_source_ids) \
				or (in_media_rating_keys and not session['ratingKey'] in in_media_rating_keys) \
				or (in_resolutions and not get_resolution(session, formatted=False) in in_resolutions) \
				or (in_channels and not get_channels(session) in in_channels) \
				or (audio_in_clients and not session['Player']['title'] in audio_in_clients) \
				or (video_in_clients and not session['Player']['title'] in video_in_clients) \
				or (get_resolution(session, formatted=False) in ex_resolutions) \
				or (session['librarySectionID'] in ex_library_source_ids) \
				or (session['ratingKey'] in ex_media_rating_keys) \
				or (get_channels(session) in ex_channels):
					logging.info('Detected session falls under exclusion rules so ignoring')
					return
				if session['Player']['title'] in audio_ex_clients:
					logging.info('Detected session falls under exclusion rules for audio; ignoring audio upgrade')
					process_audio = False
				else:
					process_audio = True
				if session['Player']['title'] in video_ex_clients:
					logging.info('Detected session falls under exclusion rules for video; ignoring video upgrade')
					process_video = False
				else:
					process_video = True
				if process_audio == False and process_video == False:
					return
				#process session if the script comes here
				media_output = ssn.get(baseurl + session['key']).json()
				part_id = ''
				for media in session['Media']:
					if 'selected' in media.keys() and media['selected'] == True:
						for part in media['Part']:
							if 'selected' in part.keys() and part['selected'] == True:
								part_id = part['id']
				if not part_id:
					logging.error('Failed to get part id')
					return
				logging.debug(json.dumps(media_output, indent=4))
				try:
					if process_audio == True and process_video == True:
						if process_priority == 'video':
							audio(session, part_id, media_output=media_output)
							video(session, part_id, media_output=media_output)
						elif process_priority == 'audio':
							video(session, part_id, media_output=media_output)
							audio(session, part_id, media_output=media_output)
						else:
							logging.error('Unknown process priority')
							exit(1)
					elif process_audio == True:
						audio(session, part_id, media_output=media_output)
					elif process_video == True:
						video(session, part_id, media_output=media_output)
				except Exception as e:
					logging.exception('Something went wrong: ')
				break
		else:
			logging.error('Detected session but couldn\'t find it in plex')
			return

if __name__  == '__main__':
	logging_level = logging.INFO
	logging.basicConfig(level=logging_level, format='[%(asctime)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S %d-%m-20%y')
	logging.info('Upgrading streams when needed...')

	backup = True if backup_plex_ip and backup_plex_port and backup_plex_api_token else False
	ssn = requests.Session()
	ssn.headers.update({'Accept':'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})
	baseurl = f'http://{plex_ip}:{plex_port}'
	plex = PlexServer(baseurl, plex_api_token)
	logging.debug(f'baseurl = {baseurl}')
	if backup == True:
		backup_ssn = requests.Session()
		backup_ssn.headers.update({'Accept':'application/json'})
		backup_ssn.params.update({'X-Plex-Token': backup_plex_api_token})
		backup_baseurl = f'http://{backup_plex_ip}:{backup_plex_port}'
		backup_plex = PlexServer(backup_baseurl, backup_plex_api_token)
		logging.debug(f'backup baseurl = {backup_baseurl}')
	if in_library_source_ids: ex_library_source_ids = []
	if in_library_target_ids: ex_library_target_ids = []
	if in_library_remote_target_ids: ex_library_remote_target_ids = []
	if in_media_rating_keys: ex_media_rating_keys = []
	if in_resolutions: ex_resolutions = []
	if in_channels: ex_channels = []
	if audio_in_clients: audio_ex_clients = []
	if video_in_clients: video_ex_clients = []

	logging.debug(f'process_priority = {process_priority}')
	try:
		listener = plex.startAlertListener(callback=process)
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		listener.stop()