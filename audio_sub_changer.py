#!/usr/bin/python3
#The use case of this script is the following:
#	Change the audio/subtitle track, based on target language, for an episode, season or entire series
#
#EXAMPLE USAGE:
#	python3 audio_sub_changer.py --Type subtitle --Language en --LibraryName Tv-series --Series 'Initial D' --SeasonNumber 5 --EpisodeNumber 1
#	python3 audio_sub_changer.py --Type audio --Language fr --LibraryName Tv-series --Series 'Into the Night'

plex_ip = ''
plex_port = ''
plex_api_token = ''

import re

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', plex_ip):
	print("Error: " + plex_ip + " is not a valid ip")
	exit(1)

if not re.search('^\d{1,5}$', plex_port):
	print("Error: " + plex_port + " is not a valid port")
	exit(1)

if not re.search('^[\w\d_-~]{19,21}$', plex_api_token):
	print("Error: " + plex_api_token + " is not a valid api token")
	exit(1)

import requests
import json
import getopt
import sys

def episode(episode_id):
	episode_output = json.loads(ssn.get(baseurl + '/library/metadata/' + str(episode_id)).text)
	part_id = []
	part_db = {}
	print(episode_output['MediaContainer']['Metadata'][0]['grandparentTitle'] + ' - S' + str(episode_output['MediaContainer']['Metadata'][0]['parentIndex']) + 'E' + str(episode_output['MediaContainer']['Metadata'][0]['index']) + ' - ' + str(episode_output['MediaContainer']['Metadata'][0]['title']))
	for media in episode_output['MediaContainer']['Metadata'][0]['Media']:
		for part in media['Part']:
			part_db[part['id']] = part
			part_id.append(part['id'])
	for part in part_id:
		selected_stream = ''
		for stream in part_db[part]['Stream']:
			if stream['streamType'] == int(type_number) and 'selected' in stream.keys() and 'languageTag' in stream.keys() and stream['languageTag'] == lang:
				selected_stream = stream
				break
		for stream in part_db[part]['Stream']:
			if stream['streamType'] == int(type_number) and 'languageTag' in stream.keys() and stream['languageTag'] == lang and not selected_stream:
				print('	Edited')
				if type == 'audio':
					ssn.put(baseurl + '/library/parts/' + str(part), params={'audioStreamID': stream['id'], 'allParts': 1})
				elif type == 'subtitle':
					ssn.put(baseurl + '/library/parts/' + str(part), params={'subtitleStreamID': stream['id'], 'allParts': 1})
				break


ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
baseurl = 'http://' + plex_ip + ':' + plex_port

section_output = json.loads(ssn.get(baseurl + '/library/sections').text)
arguments, values = getopt.getopt(sys.argv[1:], 'ht:l:L:S:s:e:', ['Help', 'Type=', 'Language=', 'LibraryName=', 'Series=', 'SeasonNumber=', 'EpisodeNumber='])
type = ''
lang = ''
lib_id = ''
series_id = ''
season_id = ''
episode_id = ''
for argument, value in arguments:
	if argument in ('-h', '--Help'):
		print('The arguments to use this script:\nIMPORTANT: The arguments need to be given in the order that they are shown here!')
		print('Required: -t/--Type [audio|subtitle], -l/--Language [ISO-639-1 (2-lowercase-letters) language code (e.g. en)], -L/--LibraryName [name of target library], -S/--Series [target series name]')
		print('Optional: -s/--SeasonNumber [number of the target season], -e/--EpisodeNumber [number of the target episode]')
		print('When --Series is given, the whole series is processed; when --SeasonNumber is given, the whole season of the series is processed; when --EpisodeNumber is given, that specific episode of that specific season is processed')
		exit()
	if argument in ('-t', '--Type'):
		if re.search('^(audio|subtitle)$', value):
			type = value
			if type == 'audio':
				type_number = 2
			elif type == 'subtitle':
				type_number = 3
		else:
			print('Error: type given is not audio or subtitle')
			exit(1)

	if argument in ('-l', '--Language'):
		if re.search('^\S{2,5}$', value): lang = value
		else:
			print('Error: language given is not a valid language code')
			exit(1)

	if argument in ('-L', '--LibraryName'):
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == str(value) and level['type'] == 'show': lib_id = level['key']
		if not lib_id:
			print('Error: library not found or not a show library')
			exit(1)

	if argument in ('-S', '--Series'):
		for level in json.loads(ssn.get(baseurl + '/library/sections/' + lib_id + '/all').text)['MediaContainer']['Metadata']:
			if level['title'] == str(value): series_id = level['ratingKey']
		if not series_id:
			print('Error: series not found or arguments not given in correct order')
			exit(1)

	if argument in ('-s', '--SeasonNumber'):
		for level in json.loads(ssn.get(baseurl + '/library/metadata/' + series_id + '/children').text)['MediaContainer']['Metadata']:
			if level['index'] == int(value): season_id = level['ratingKey']
		if not season_id:
			print('Error: season not found or arguments not given in correct order')
			exit(1)

	if argument in ('-e', '--EpisodeNumber'):
		for level in json.loads(ssn.get(baseurl + '/library/metadata/' + season_id + '/children').text)['MediaContainer']['Metadata']:
			if level['index'] == int(value): episode_id = level['ratingKey']
		if not episode_id:
			print('Error: episode not found or arguments not given in correct order')
			exit(1)

if not lib_id or not lang or not type or not series_id:
	print('Error: Required arguments were not all given\nrun audio_sub_changer.py -h')
	exit(1)

if episode_id:
	#change an episode
	episode(episode_id)
elif season_id:
	#change a season
	for episodes in json.loads(ssn.get(baseurl + '/library/metadata/' + season_id + '/children').text)['MediaContainer']['Metadata']:
		episode(episodes['ratingKey'])
elif series_id:
	#change a series
	for seasons in json.loads(ssn.get(baseurl + '/library/metadata/' + series_id + '/children').text)['MediaContainer']['Metadata']:
		for episodes in json.loads(ssn.get(baseurl + '/library/metadata/' + seasons['ratingKey'] + '/children').text)['MediaContainer']['Metadata']:
			episode(episodes['ratingKey'])
