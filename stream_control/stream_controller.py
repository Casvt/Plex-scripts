#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	When a local stream is started, check if a different version of the media exists that better matches the desired criteria (resolution or audio channel count).
	This version can exist in the same folder, in a differnt library or on a different plex server
	When a better version is found, switch the stream to that version
Requirements (python3 -m pip install [requirement]):
	requests
	PlexAPI
Setup:
	Fill the variables below firstly,
	then go to the tautulli web-ui -> Settings -> Notification Agents -> Add a new notification agent -> Script:
		Configuration:
			Script Folder = /path/to/script/folder
			Script File = select this script
			Script Timeout = 60
			Description = whatever you want
		Triggers:
			Playback Start = check
		Conditions:
			-- Parameter -- = Stream Location
			-- Operator -- = is
			-- Value -- = lan
		Arguments:
			Playback Start -> Script Arguments = --Player {player} --RatingKey {rating_key} --Resolution {stream_video_full_resolution} --Channels {stream_audio_channels} --VideoResolution {video_resolution} --AudioChannels {audio_channels} --ViewOffset {progress_duration_sec}
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

#optional; if you want to search on a different plex server too
backup_plex_ip = ''
backup_plex_port = ''
backup_plex_api_token = ''

#--------------------
#PROCESS

process_video = True
process_audio = True
#what is more important when trying to find versions for the media
process_priority = 'video' # 'video' or 'audio'
#process direction:
# 'up': try to find a version that has a better resolution or higher audio channel count
# 'down': when a stream is transcoding, try to find a version that has a resolution or audio channel count as close as possible to the transcoded values to reduce transcoding load
process_direction = 'up'

#--------------------
#INCLUSION AND EXCLUSION

# include_clients OVERRULES exclude_clients IF BOTH ARE GIVEN VALUES
#list of client names to >only< process
include_clients = []
#list of client names to >not< process
exclude_clients = []

#upgrade streams no further than this resolution/channel count
#allowed values for max_resolution are '480','720','1080','2k','4k','6k','8k'
max_resolution = '4k'
max_channel_count = 9 # 7.2 = 9, 5.1.2 = 8, etc.

#--------------------

from os import getenv

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"
backup_plex_ip = getenv('backup_plex_ip', backup_plex_ip)
backup_plex_port = getenv('backup_plex_port', backup_plex_port)
backup_plex_api_token = getenv('backup_plex_api_token', backup_plex_api_token)
backup_base_url = f"http://{backup_plex_ip}:{backup_plex_port}"
resolution_ladder = ['480','720','1080','2k','4k','6k','8k']
type_map = {
	'movie': ('movie',1),
	'episode': ('show', 4)
}

def _extract_streams(media_info: dict, server: str) -> tuple:
	video_result, audio_result = [], []
	for media_index, media in enumerate(media_info['MediaContainer']['Metadata'][0]['Media']):
		for part in media['Part']:
			for stream in part['Stream']:
				if not stream['streamType'] in (1,2): continue
				result = {
					'id': stream['id'],
					'part_id': part['id'],
					'media_index': media_index,
					'media_id': media['id'],
					'rating_key': media_info['MediaContainer']['Metadata'][0]['ratingKey'],
					'server': server,

					'streamType': stream['streamType'],
					'index': stream['index'],
					'selected': 'selected' in stream,

					'resolution': media['videoResolution'],
					'channel_count': stream.get('channels',0)
				}
				if stream['streamType'] == 1: video_result.append(result)
				elif stream['streamType'] == 2: audio_result.append(result)
	return video_result, audio_result

def _find_version(ssn, media_info: dict, resolution: str, channels: int, video_resolution: str, audio_channels: int) -> tuple:
	video_result, audio_result = [], []
	#map all available versions and their streams
	#search inside library entry
	result = _extract_streams(media_info, server='main')
	video_result += result[0]
	audio_result += result[1]

	#search inside other libraries
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
	media_type = type_map[media_info['MediaContainer']['Metadata'][0]['type']]
	for lib in sections:
		if lib['type'] != media_type[0]: continue
		if lib['key'] == str(media_info['MediaContainer']['librarySectionID']): continue
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'type': media_type[1], 'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])
		for media in lib_output:
			if media['Guid'] == media_info['MediaContainer']['Metadata'][0]['Guid']:
				#found media in other library
				media_entry_info = ssn.get(f'{base_url}/library/metadata/{media["ratingKey"]}').json()
				result = _extract_streams(media_entry_info, server='main')
				video_result += result[0]
				audio_result += result[1]
				break
		else:
			continue
		break

	#search on backup server
	if backup_plex_ip and backup_plex_port and backup_plex_api_token:
		ssn.params.update({'X-Plex-Token': backup_plex_api_token})
		sections = ssn.get(f'{backup_base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
		for lib in sections:
			if lib['type'] != media_type[0]: continue
			lib_output = ssn.get(f'{backup_base_url}/library/sections/{lib["key"]}/all', params={'type': media_type[1], 'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])
			for media in lib_output:
				if media['Guid'] == media_info['MediaContainer']['Metadata'][0]['Guid']:
					#found media on backup server
					media_entry_info = ssn.get(f'{backup_base_url}/library/metadata/{media["ratingKey"]}').json()
					result = _extract_streams(media_entry_info, server='backup')
					video_result += result[0]
					audio_result += result[1]
					break
			else:
				continue
			break

		ssn.params.update({'X-Plex-Token': plex_api_token})

	#filter and sort streams
	if process_video == True and process_audio == False:
		if process_direction == 'down':
			video_result = list(filter(lambda m: resolution_ladder.index(resolution) <= resolution_ladder.index(m['resolution']) < resolution_ladder.index(video_resolution), video_result))
			video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']))
		else: #up
			video_result = list(filter(lambda m: resolution_ladder.index(resolution) < resolution_ladder.index(m['resolution']) <= resolution_ladder.index(max_resolution), video_result))
			video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']), reverse=True)

	elif process_audio == True and process_video == False:
		if process_direction == 'down':
			audio_result = list(filter(lambda m: channels <= m['channel_count'] < audio_channels, audio_result))
			audio_result.sort(key=lambda m: m['channel_count'])
		else: #up
			audio_result = list(filter(lambda m: channels < m['channel_count'] <= max_channel_count, audio_result))
			audio_result.sort(key=lambda m: m['channel_count'], reverse=True)

	else:
		if process_direction == 'down':
			if process_priority == 'video':
				#get all video streams between transcoding resolution and original stream resolution (tr <= s < or)
				video_result = list(filter(lambda m: resolution_ladder.index(resolution) <= resolution_ladder.index(m['resolution']) < resolution_ladder.index(video_resolution), video_result))
				video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']))
				#keep the video streams closest to transcoding resolution
				video_result = list(filter(lambda m: m['resolution'] == video_result[0]['resolution'], video_result))
				if len(video_result) == 1:
					#there is one video stream that better fits the stream
					audio_result = list(filter(lambda m: m['part_id'] == video_result[0]['part_id'] and m['server'] == video_result[0]['server'], audio_result))
					audio_result.sort(key=lambda m: m['channel_count'], reverse=True)
					audio_result.sort(key=lambda m: abs(channels - m['channel_count']))
				elif video_result:
					#there are multiple video streams that better fit the stream; find the one that has a better fitting audio stream
					part_ids = [(a['part_id'], a['server']) for a in video_result]
					audio_result = list(filter(lambda m: (m['part_id'], m['server']) in part_ids, audio_result))
					audio_result.sort(key=lambda m: m['channel_count'], reverse=True)
					audio_result.sort(key=lambda m: abs(channels - m['channel_count']))
					video_result = list(filter(lambda m: m['part_id'] == audio_result[0]['part_id'] and m['server'] == audio_result[0]['server'], video_result))
				else:
					#there is no video stream that is closer to transcoding resolution than the current one; find a better fitting audio stream where the video stream of the file matches the current resolution
					audio_result = list(filter(lambda m: channels <= m['channel_count'] < audio_channels, audio_result))
					audio_result.sort(key=lambda m: m['channel_count'])
				#get the audio stream closest to the current transcoding channel count
				audio_result.sort(key=lambda m: m['channel_count'])
			else: #'audio'
				#get all audio streams between transcoding channel count and original stream channel count (tcc <= s < occ)
				audio_result = list(filter(lambda m: channels <= m['channel_count'] < audio_channels, audio_result))
				audio_result.sort(key=lambda m: m['channel_count'])
				#keep the audio streams closest to transcoding channel count
				audio_result = list(filter(lambda m: m['channel_count'] == audio_result[0]['channel_count'], audio_result))
				if len(audio_result) == 1:
					#there is one audio stream that better fits the stream
					video_result = list(filter(lambda m: m['part_id'] == audio_result[0]['part_id'] and m['server'] == audio_result[0]['server'], video_result))
				elif audio_result:
					#there are multiple audio streams that all fit the stream the best; it doesn't matter which one we use so choose the one that has the video stream that best matches the transcoding video resolution
					part_ids = [(a['part_id'], a['server']) for a in audio_result]
					video_result = list(filter(lambda m: (m['part_id'], m['server']) in part_ids, video_result))
					video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']), reverse=True)
					video_result.sort(key=lambda m: abs(resolution_ladder.index(resolution) - resolution_ladder.index(m['resolution'])))
					audio_result = list(filter(lambda m: m['part_id'] == video_result[0]['part_id'] and m['server'] == video_result[0]['server'], audio_result))
				else:
					#there are no audio streams that fit better; find better fitting video stream
					video_result = list(filter(lambda m: resolution_ladder.index(resolution) <= resolution_ladder.index(m['resolution']) < resolution_ladder.index(video_resolution), video_result))
					video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']))

		else: #up
			if process_priority == 'video':
				#get all video streams between transcoding resolution and max allowed resolution (tr < s <= mr)
				video_result = list(filter(lambda m: resolution_ladder.index(resolution) < resolution_ladder.index(m['resolution']) <= resolution_ladder.index(max_resolution), video_result))
				video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']), reverse=True)
				#keep the highest resolution video streams
				video_result = list(filter(lambda m: resolution_ladder.index(m['resolution']) == resolution_ladder.index(video_result[0]['resolution']), video_result))
				if len(video_result) == 1:
					#there is one video stream that is higher quality than the stream
					audio_result = list(filter(lambda m: m['part_id'] == video_result[0]['part_id'] and m['server'] == video_result[0]['server'], audio_result))
					audio_result.sort(key=lambda m: m['channel_count'], reverse=True)
				elif video_result:
					#there are multiple video streams that all fit the stream best; get the one with the highest audio channel count
					part_ids = [(a['part_id'], a['server']) for a in video_result]
					audio_result = list(filter(lambda m: (m['part_id'], m['server']) in part_ids, audio_result))
					audio_result.sort(key=lambda m: m['channel_count'], reverse=True)
					video_result = list(filter(lambda m: m['part_id'] == audio_result[0]['part_id'] and m['server']  == audio_result[0]['server'], video_result))
				else:
					#there are no video streams that fit better; find better fitting audio stream
					audio_result = list(filter(lambda m: channels < m['channel_count'] <= max_channel_count, audio_result))
					audio_result.sort(key=lambda m: (m['channel_count'], resolution_ladder.index(m['resolution'])), reverse=True)
			else: #audio
				#get all audio streams between transcoding channel count and max allowed channel count (tcc < s <= mcc)
				audio_result = list(filter(lambda m: channels < m['channel_count'] <= max_channel_count, audio_result))
				audio_result.sort(key=lambda m: m['channel_count'], reverse=True)
				#keep the highest channel count audio streams
				audio_result = list(filter(lambda m: m['channel_count'] == audio_result[0]['channel_count'], audio_result))
				if len(audio_result) == 1:
					#there is one audio stream that has a higher channel count than the stream
					video_result = list(filter(lambda m: m['part_id'] == audio_result[0]['part_id'] and m['server'] == audio_result[0]['server'], video_result))
					video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']), reverse=True)
				elif audio_result:
					#there are multiple audio streams that all fit the stream best; get the one with the highest resolution video stream
					part_ids = [(a['part_id'], a['server']) for a in audio_result]
					video_result = list(filter(lambda m: (m['part_id'], m['server']) in part_ids, video_result))
					video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']), reverse=True)
					audio_result = list(filter(lambda m: m['part_id'] == video_result[0]['part_id'] and m['server']  == video_result[0]['server'], audio_result))
				else:
					#there are no audio streams that fit better; find better fitting video stream
					video_result = list(filter(lambda m: resolution_ladder.index(resolution) < resolution_ladder.index(m['resolution']) <= resolution_ladder.index(max_resolution), video_result))
					video_result.sort(key=lambda m: resolution_ladder.index(m['resolution']), reverse=True)

	return video_result, audio_result

def stream_controller(
	ssn, plex, player: str, rating_key: str,
	resolution: str, channels: int, video_resolution: str, audio_channels: int, view_offset: int,
	backup_plex=None
):
	result_json = [rating_key]
	view_offset = view_offset * 1000

	#check if stream should be processed
	if not (process_video and process_audio): return
	if include_clients and not player in include_clients: return
	if exclude_clients and player in exclude_clients: return

	#check for better versions
	media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}', params={'includeGuids': '1'}).json()
	video_result, audio_result = _find_version(ssn, media_info, resolution.rstrip('p'), channels, video_resolution.rstrip('p'), audio_channels)

	#change stream if needed
	if not video_result and not audio_result: return result_json
	client = plex.client(player)
	if not video_result and audio_result:
		client.setAudioStream(audioStreamID=str(audio_result[0]['id']), mtype='video')
	else:
		client.stop(mtype='video')
		if video_result[0]['server'] == 'main':
			media = plex.fetchItem(f'/library/metadata/{video_result[0]["rating_key"]}')
			client.playMedia(media, offset=view_offset, mediaIndex=video_result[0]['media_index'])
			if audio_result:
				client.setAudioStream(audioStreamID=audio_result[0]['id'], mtype='video')
		else: #backup
			media = backup_plex.fetchItem(f'/library/metadata/{video_result[0]["rating_key"]}')
			backup_client = backup_plex.client(player)
			backup_client.playMedia(media, offset=view_offset, mediaIndex=video_result[0]['media_index'])
			if audio_result:
				backup_client.setAudioStream(audioStreamID=audio_result[0]['id'], mtype='video')

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser
	from plexapi.server import PlexServer

	#setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})
	plex = PlexServer(base_url, plex_api_token)
	if backup_plex_ip and backup_plex_port and backup_plex_api_token:
		backup_plex = PlexServer(backup_base_url, backup_plex_api_token)
	else:
		backup_plex = None

	#check / fix variables and argument parsing
	if include_clients and exclude_clients:
		exclude_clients = []
	if not max_resolution:
		max_resolution = '4k'
	if not max_channel_count:
		max_channel_count = '9'
	if not process_priority:
		process_priority = 'video'
	if not process_direction:
		process_direction = 'up'

	#setup arg parsing
	parser = ArgumentParser(description='When a local stream is started, check if a different version of the media exists that better matches the desired criteria (resolution or audio channel count).')
	parser.add_argument('-p','--Player', type=str, help='The name of the player used for the stream', required=True)
	parser.add_argument('-k','--RatingKey', type=str, help='The rating key of the media being streamed', required=True)
	parser.add_argument('-r','--Resolution', type=str, help='The resolution of the stream', required=True)
	parser.add_argument('-c','--Channels', type=int, help='The channel count of the stream', required=True)
	parser.add_argument('-R','--VideoResolution', type=str, help='The resolution of the stream inside the file', required=True)
	parser.add_argument('-C','--AudioChannels', type=int, help='The channel count of the stream inside the file', required=True)
	parser.add_argument('-v','--ViewOffset', type=int, help='The offfset of the stream', required=True)

	args = parser.parse_args()
	#call function and process result
	response = stream_controller(ssn=ssn, plex=plex, player=args.Player, rating_key=args.RatingKey, resolution=args.Resolution, channels=args.Channels, video_resolution=args.VideoResolution, audio_channels=args.AudioChannels, view_offset=args.ViewOffset, backup_plex=backup_plex)
	if not isinstance(response, list):
		parser.error(response)
