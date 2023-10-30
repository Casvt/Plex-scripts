#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Change the audio/subtitle track, based on target language, forced status, codec, title and/or channel count (audio) for an episode, season, series, movie, entire movie/show library or all libraries
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	You can find examples of the usage below.
Examples:
	--Type audio --Language fr --Language en --ChannelCount 6 --Forced avoid --LibraryName Tv-series --LibraryName Tv-series-2
		Set the audio for all episodes of all series in the 'Tv-series' and 'Tv-series-2' library.
		Try to set the audio track to French but otherwise English.
		If possible, choose the audio stream with 6 channels (5.1) but avoid the stream if it's marked as forced.

	--Type subtitle --Language en --Codec ass --LibraryName Tv-series --Series 'Initial D' --SeasonNumber 5
		Set the subtitle for season 5 of the series 'Initial D' in the 'Tv-series' library.
		Try to set the subtitle track to one with the language English and, if possible, the codec ass.

	--Type subtitle --Language en --TitleContains 'songs' --LibraryName Films --Movie '2 Fast 2 Furious' --Movie 'The Fast and The Furious'
		Set the subtitle for the movies '2 Fast 2 Furious' and 'The Fast and The Furious' inside the 'Films' library.
		Try to set the subtitle to one with the language English, prefering subtitles that have 'songs' in the title.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from typing import Dict, List

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

langs = ['aa', 'ab', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'br', 'bs',
	'ca', 'ce', 'ch', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv', 'dz', 'ee', 'el', 'en', 'en-US', 'en-GB', 'en-AU', 'eo', 'es', 'et', 'eu',
	'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz',
	'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky',
	'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my',
	'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps', 'pt', 'qu',
	'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st', 'su', 'sv', 'sw',
	'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty', 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo', 'wa', 'wo',
	'xh', 'yi', 'yo', 'za', 'zh', 'zu'
]
types = {
	'audio': 2,
	'subtitle': 3
}

def _sort_streams(
	x: dict, 
	language: Dict[str, int],
	channel_count: int,
	forced: str,
	codec: Dict[str, int],
	title_contains: str
) -> tuple:
	"Give ranking to a stream based on what is prefered"
	forced = int(not ((forced == 'prefer' and x['forced'])
					or (forced == 'avoid' and not x['forced'])))

	language = language.get(x['language'], float('inf'))

	channel_count = int(channel_count and x['channels'] != channel_count)

	codec = codec.get(x['codec'], float('inf'))

	title_contains = int(not (title_contains and title_contains in x.get('title', '')))

	order = (forced, language, channel_count, codec, title_contains)
	return order

def _set_track(
	ssn, user_data: dict, rating_key: str, type: int,
	language: Dict[str, int], forced: str, codec: Dict[str, int], title_contains: str, channel_count: int
) -> bool:
	"This function scans the tracks of the media and determines the best one and applies it"	
	updated = False
	media_output = ssn.get(f'{base_url}/library/metadata/{rating_key}').json()['MediaContainer']['Metadata'][0]
	for media in media_output['Media']:
		for part in media['Part']:
			# Get all streams and note down their information
			streams = []
			for stream in part['Stream']:
				if not stream['streamType'] == type: continue
				streams.append({
					'language': stream.get('languageTag','und'),
					'id': stream['id'],
					'forced': 'forced' in stream,
					'codec': stream.get('codec'),
					'channels': stream.get('channels',-1),
					'title': stream.get('title'),
					'selected': 'selected' in stream
				})
			if not streams: continue

			# Sort the streams based on preferences
			streams.sort(key=lambda x: _sort_streams(x, language, channel_count, forced, codec, title_contains))
			if not streams[0]['selected']: updated = True

			# Apply choice
			for user_token in user_data.values():
				if type == 2:
					ssn.put(
						f'{base_url}/library/parts/{part["id"]}',
						params={
							'audioStreamID': streams[0]['id'],
							'allParts': 0,
							'X-Plex-Token': user_token
						}
					)

				elif type == 3:
					ssn.put(
						f'{base_url}/library/parts/{part["id"]}',
						params={
							'subtitleStreamID': streams[0]['id'],
							'allParts': 0,
							'X-Plex-Token': user_token
						}
					)

	return updated

def audio_sub_changer(
	ssn, type: str, language: list, forced: str, codec: list, title_contains: str, channel_count: int,
	all: bool, all_movie: bool=False, all_show: bool=False,
	library_names: List[str]=[],
	movie_names: list=[],
	series_name: str=None, season_number: int=None, episode_number: int=None,
	users: list=['@me']
) -> List[int]:
	result_json = []
	language: Dict[str, int] = {l: i for i, l in enumerate(language)}
	codec: Dict[str, int] = {l: i for i, l in enumerate(codec)}
	lib_target_specifiers = (library_names,movie_names,series_name,season_number,episode_number)
	all_target_specifiers = (all_movie, all_show)

	# Check for illegal arg parsing
	if not language: return 'Language required to be given'
	for lang in language:
		if not lang in langs:
			return f'Invalid language: {lang}'
	if not type in types:
		return 'Unknown type'
	if all:
		if lib_target_specifiers.count(None) < len(lib_target_specifiers) or True in all_target_specifiers:
			return 'Both "all" and a target-specifier are set'
	else:
		if not True in all_target_specifiers and not library_names:
			return '"all" is set to False but no target-specifier is given'
		if season_number is not None and series_name is None:
			# Season number given but no series name
			return '"season_number" is set but not "series_name"'
		if episode_number is not None and (season_number is None or series_name is None):
			# Episode number given but no season number or no series name
			return '"episode_number" is set but not "season_number" or "series_name"'
	type = types[type]

	args = {
		'type': type,
		'language': language,
		'forced': forced,
		'codec': codec,
		'title_contains': title_contains,
		'channel_count': channel_count
	}

	# Get tokens of users
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers').text
	user_data = dict(map(lambda r: r.split('"')[0:7:6], shared_users.split('username="')[1:]))
	user_data['@me'] = plex_api_token
	if not '@all' in users:
		user_data = {k: v for k, v in user_data.items() if k in users}

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
	for lib in sections:
		if not (
			all and lib['type'] in ('movie', 'show')
			or all_movie and lib['type'] == 'movie'
			or all_show and lib['type'] == 'show'
			or lib['title'] in library_names
		):
			continue

		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer'].get('Metadata',[])

		if lib['type'] == 'movie':
			for movie in lib_output:
				if movie_names and not movie['title'] in movie_names:
					continue

				print(f'	{movie["title"]}')
				result = _set_track(ssn=ssn, user_data=user_data, rating_key=movie['ratingKey'], **args)
				if result:
					print('		Updated')
				result_json.append(movie['ratingKey'])


		elif lib['type'] == 'show':
			for show in lib_output:
				if series_name is not None and show['title'] != series_name:
					continue

				print(f'	{show["title"]}')
				show_output = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer'].get('Metadata', [])
				# Loop through episodes of show to check if targeted season exists
				if season_number is not None:
					for episode in show_output:
						if episode['parentIndex'] == season_number:
							break
					else:
						return 'Season not found'

				# Loop through episodes of show
				for episode in show_output:
					if season_number is not None and episode['parentIndex'] != season_number:
						# A specific season is targeted and this one is not it; so skip
						continue

					if episode_number is not None and episode['index'] != episode_number:
						# This season is targeted but this episode is not; so skip
						continue

					print(f'		S{episode["parentIndex"]}E{episode["index"]}	- {episode["title"]}')
					result = _set_track(ssn=ssn, user_data=user_data, rating_key=episode['ratingKey'], **args)
					if result:
						print('			Updated')
					result_json.append(episode['ratingKey'])

					if episode_number is not None:
						break
				else:
					if episode_number is not None:
						return 'Episode not found'

				if series_name is not None:
					break
			else:
				if series_name is not None:
					return 'Series not found'
		else:
			return 'Library not supported'
		break
	else:
		return 'Library not found'

	return result_json

if __name__ == '__main__':
	from argparse import ArgumentParser

	from requests import Session

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	# Setup arg parsing
	parser = ArgumentParser(description="Change the audio/subtitle track, based on target language, forced status, codec, title and/or channel count (audio) for an episode, season, series, movie or entire movie/show library")
	parser.add_argument('-t', '--Type', choices=types.keys(), help="Give the type of stream to change", required=True)

	parser.add_argument('-L', '--Language', action='append', help="ISO-639-1 language code (2 lowercase letters e.g. 'en') to try to set the stream to; give multiple times to setup a preference order", required=True)
	parser.add_argument('-f', '--Forced', choices=['avoid','prefer'], help='How forced streams should be treated; default is "avoid"', default='avoid')
	parser.add_argument('-c', '--Codec', action='append', help="Name of stream codec to prefer; give multiple times to setup a preference order", default=[])
	parser.add_argument('-T', '--TitleContains', type=str, help="Give preference to streams that have the given value in their title", default='')
	parser.add_argument('-C', '--ChannelCount', type=int, help="AUDIO ONLY: Give preference to streams that have the given amount of audio channels", default=-1)

	parser.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	parser.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	parser.add_argument('--AllShow', action='store_true', help='Target all show libraries')

	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target library; allowed to give argument multiple times", action='append', default=[], required=True)
	parser.add_argument('-m', '--MovieName', type=str, help="Target a specific movie inside a movie library based on it's name (only accepted when -l is a movie library); allowed to give argument multiple times", action='append', default=[])
	parser.add_argument('-s', '--SeriesName', type=str, help="Target a specific series inside a show library based on it's name (only accepted when -l is a show library)")
	parser.add_argument('-S', '--SeasonNumber', type=int, help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given) (specials is 0)")
	parser.add_argument('-e', '--EpisodeNumber', type=int, help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given)")
	parser.add_argument('-u', '--User', type=str, help="Select the user(s) to apply this script to; Give username, '@me' for yourself or '@all' for everyone; allowed to give argument multiple times", action='append', default=['@me'])

	args = parser.parse_args()
	# Call function and process result
	response = audio_sub_changer(
		ssn=ssn, type=args.Type,
		language=args.Language, forced=args.Forced, codec=args.Codec,
		title_contains=args.TitleContains, channel_count=args.ChannelCount,
		all=args.All, all_movie=args.AllMovie, all_show=args.AllShow,
		library_names=args.LibraryName,
		movie_names=args.MovieName,
		series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber,
		users=args.User
	)
	if not isinstance(response, list):
		if response == 'Both "all" and a target-specifier are set':
			parser.error('Both -a/--All and a target-specifier are set')

		elif response == '"all" is set to False but no target-specifier is given':
			parser.error('-a/--All is not set but also no target-specifier is set')

		elif response == '"season_number" is set but not "series_name"':
			parser.error('-S/--SeasonNumber given but not -s/--SeriesName given')

		elif response == '"episode_number" is set but not "season_number" or "series_name"':
			parser.error('-e/--EpisodeNumber given but -S/--SeasonNumber or -s/--SeriesName not given')

		else:
			parser.error(response)
