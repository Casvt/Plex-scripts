#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Change the audio/subtitle track, based on target language, forced status,
	codec, title strings and/or channel count (audio) for a movie/episode
	up to all movie/show libraries.

Requirements (python3 -m pip install [requirement]):
	requests

Setup:
	1. Fill the variables below.
	2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
		python3 audio_sub_changer.py -h
		or
		python audio_sub_changer.py -h

Examples:
	--Type audio --Language fr --Language en --ChannelCount 6 --Forced avoid --LibraryName "Tv-series" --LibraryName "Tv-series-2"

		Set the audio for all episodes of all series in the 'Tv-series' and 'Tv-series-2' library.
		Try to set the audio track to French but otherwise English.
		If possible, choose the audio stream with 6 channels (5.1) but avoid the stream if it's marked as forced.

	--Type subtitle --Language en --Codec ass --LibraryName Tv-series --Series 'Initial D' --SeasonNumber 5 --SeasonNumber 6

		Set the subtitle for season 5 and 6 of the series 'Initial D' in the 'Tv-series' library.
		Try to set the subtitle track to one with the language English and, if possible, the codec ass.

	--Type subtitle --Language en --TitleContains 'songs' --LibraryName Films --Movie '2 Fast 2 Furious' --Movie 'The Fast and The Furious'

		Set the subtitle for the movies '2 Fast 2 Furious' and 'The Fast and The Furious' inside the 'Films' library.
		Try to set the subtitle to one with the language English, prefering subtitles that have 'songs' in the title.
"""

#===== FILL THESE VARIABLES =====
plex_base_url = ''
plex_api_token = ''
#================================

from dataclasses import dataclass, field
from enum import Enum
from os import getenv
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Union

if TYPE_CHECKING:
	from requests import Session

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = plex_base_url.rstrip('/')

langs = {'aa', 'ab', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'br', 'bs',
	'ca', 'ce', 'ch', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv', 'dz', 'ee', 'el', 'en', 'en-US', 'en-GB', 'en-AU', 'eo', 'es', 'et', 'eu',
	'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz',
	'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky',
	'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my',
	'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps', 'pt', 'qu',
	'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st', 'su', 'sv', 'sw',
	'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty', 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo', 'wa', 'wo',
	'xh', 'yi', 'yo', 'za', 'zh', 'zu'
}


class TrackType(Enum):
	audio = 2
	subtitle = 3


@dataclass
class StreamFilter:
	language: List[str] = field(default_factory=lambda: [])
	prefer_forced: bool = False
	codec: List[str] = field(default_factory=lambda: [])
	title_contains: List[str] = field(default_factory=lambda: [])
	channel_count: Union[int, None] = None

	def __post_init__(self):
		if not self.language:
			raise ValueError("The key 'language' requires a non-empty list")
		for lang in self.language:
			if not lang in langs:
				raise ValueError(f"Unknown language: {lang}")

		self.lang_pref: Dict[str, int] = {l: i for i, l in enumerate(self.language)}
		self.codec_pref: Dict[str, int] = {l: i for i, l in enumerate(self.codec)}

		return


@dataclass
class LibraryFilter:
	all: bool = False
	all_movie: bool = False
	all_show: bool = False
	libraries: List[str] = field(default_factory=lambda: [])
	movies: List[str] = field(default_factory=lambda: [])
	series: List[str] = field(default_factory=lambda: [])
	season_numbers: List[int] = field(default_factory=lambda: [])
	episode_numbers: List[int] = field(default_factory=lambda: [])

	def __post_init__(self):
		self.content_specifiers = (
			self.libraries,
			self.movies,
			self.series, self.season_numbers, self.episode_numbers
		)
		self.lib_specifiers = (
			self.all_movie, self.all_show
		)

		if self.all:
			if (
				any(self.content_specifiers)
				or True in self.lib_specifiers
			):
				raise ValueError("Can't combine the 'all' target specifier with any other target specifier")

		else:
			if not True in self.lib_specifiers and not self.libraries:
				raise ValueError("Either have to select all libraries of a type or supply library names")

			if len(self.series) > 1:
				if self.season_numbers:
					# Season numbers with multiple series
					raise ValueError("Can't give season numbers for multiple series")

				elif self.episode_numbers:
					# Episode numbers with multiple series
					raise ValueError("Can't give episode numbers for multiple series")

			elif len(self.series) == 1:
				if self.episode_numbers:
					if not self.season_numbers:
						# Episode numbers without a season
						raise ValueError("Can't give episode numbers without specifying a season number")

					elif len(self.season_numbers) > 1:
						# Episode numbers with multiple seasons
						raise ValueError("Can't give episode numbers with multiple seasons")

			else:
				# No series specified
				if self.season_numbers:
					# Season numbers but no series
					raise ValueError("Can't give season numbers without specifying a series")

				elif self.episode_numbers:
					# Episode numbers but no series
					raise ValueError("Can't give episode numbers without specifying a series")

		return


def _get_library_entries(
	ssn: 'Session',
	library_filter: LibraryFilter
) -> Generator[Dict[str, Any], Any, Any]:
	"""Get library entries to iterate over.

	Args:
		ssn (Session): The plex requests session to fetch with.
		library_filter (LibraryFilter): The filters to apply to the media.

	Yields:
		Generator[Dict[str, Any], Any, Any]: The resulting media information.
	"""
	lf = library_filter

	sections: List[dict] = ssn.get(
		f'{base_url}/library/sections'
	).json()['MediaContainer'].get('Directory', [])

	for lib in sections:
		if not (
			lib['type'] in ('movie', 'show')
			and
				lf.all
				or lf.all_movie and lib['type'] == 'movie'
				or lf.all_show and lib['type'] == 'show'
				or lf.libraries and lib['title'] in lf.libraries
		):
			continue

		print(lib['title'])
		lib_output: List[dict] = ssn.get(
			f'{base_url}/library/sections/{lib["key"]}/all'
		).json()['MediaContainer'].get('Metadata',[])

		if lib['type'] == 'movie':
			for movie in lib_output:
				if lf.movies and not movie['title'] in lf.movies:
					continue

				print(f'	{movie["title"]}')
				yield movie

		elif lib['type'] == 'show':
			for show in lib_output:
				if lf.series and not show['title'] in lf.series:
					continue

				print(f'	{show["title"]}')
				show_output: List[dict] = ssn.get(
					f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves'
				).json()['MediaContainer'].get('Metadata', [])

				for episode in show_output:
					if lf.season_numbers and not episode['parentIndex'] in lf.season_numbers:
						continue

					if lf.episode_numbers and not episode['index'] in lf.episode_numbers:
						continue

					print(f'		S{episode["parentIndex"]}E{episode["index"]}')
					yield episode
	return


def _gather_user_tokens(ssn: 'Session', users: List[str] = ['@me']) -> List[str]:
	"""Get api tokens based on user list.

	Args:
		ssn (Session): The plex requests session to fetch with.
		users (List[str], optional): The list of users to get the tokens of.
			Defaults to ['@me'].

	Returns:
		List[str]: The list of tokens.
	"""
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers').text
	user_data = dict(map(lambda r: r.split('"')[0:7:6], shared_users.split('username="')[1:]))
	user_data['@me'] = plex_api_token
	if not '@all' in users:
		return [v for k, v in user_data.items() if k in users]
	else:
		return list(user_data.values())


def _sort_streams(
	stream: dict,
	stream_filter: StreamFilter
) -> tuple:
	"""Give a sorting position for a stream based on preference.

	Args:
		stream (dict): The stream to give the sorting position for.
		stream_filter (StreamFilter): The preference to base the position on.

	Returns:
		tuple: The sorting position.
	"""
	sf = stream_filter

	return (
		not (sf.prefer_forced == stream['forced']),

		sf.lang_pref.get(stream['language'], float('inf')),

		sf.channel_count is not None and not (stream['channels'] == sf.channel_count),

		sf.codec_pref.get(stream['codec'], float('inf')),

		sf.title_contains is not None and not any(t in stream['title'] for t in sf.title_contains),
	)


def _set_track(
	ssn: 'Session', user_tokens: List[str], rating_key: str,
	type: TrackType, stream_filter: StreamFilter
) -> bool:
	"""Select a track for the media based on preferences.

	Args:
		ssn (Session): The plex requests session to fetch with.
		user_tokens (List[str]): The tokens of the users to set the track for.
		rating_key (str): The ratingKey of the media to process.
		type (TrackType): The type of track to evaluate.
		stream_filter (StreamFilter): The preferences.

	Returns:
		bool: Whether or not the selection has been updated.
	"""
	updated = False
	media_output: Dict[str, List[Dict[str, List[Dict[str, List[dict]]]]]] = ssn.get(
		f'{base_url}/library/metadata/{rating_key}'
	).json()['MediaContainer']['Metadata'][0]

	for media in media_output.get('Media', []):
		for part in media.get('Part', []):
			# Get all streams and note down their information
			streams = []
			for stream in part.get('Stream', []):
				if not stream['streamType'] == type.value:
					continue

				streams.append({
					'language': stream.get('languageTag','und'),
					'id': stream['id'],
					'forced': 'forced' in stream,
					'codec': stream.get('codec'),
					'channels': stream.get('channels',-1),
					'title': stream.get('title', ''),
					'selected': 'selected' in stream
				})

			if not streams:
				continue

			# Sort the streams based on preferences
			streams.sort(key=lambda s: _sort_streams(s, stream_filter))
			if not streams[0]['selected']:
				updated = True

			# Apply choice
			key = 'audioStreamID' if type.value == 2 else 'subtitleStreamID'
			for user_token in user_tokens:
				ssn.put(
					f'{base_url}/library/parts/{part["id"]}',
					params={
						key: streams[0]['id'],
						'allParts': 0,
						'X-Plex-Token': user_token
					}
				)

	return updated


def audio_sub_changer(
	ssn: 'Session', library_filter: LibraryFilter,
	type: TrackType, stream_filter: StreamFilter,
	users: List[str] = ['@me']
) -> List[int]:
	"""Change the audio/subtitle track, based on target language, forced status,
	codec, title strings and/or channel count (audio) for a movie/episode
	up to all movie/show libraries.

	Args:
		ssn (Session): The plex requests session to fetch with.
		library_filter (LibraryFilter): The filter to apply to the media.
		type (TrackType): The type of media track that needs to be changed.
		stream_filter (StreamFilter): The stream preference to base the selection on.
		users (List[str], optional): The list of users to apply the selection for.
			Defaults to ['@me'].

	Returns:
		List[int]: List of media rating keys that were processed.
	"""
	result_json = []
	user_tokens = _gather_user_tokens(ssn, users)

	for media in _get_library_entries(ssn, library_filter):
		result = _set_track(
			ssn, user_tokens,
			media["ratingKey"], type,
			stream_filter
		)
		if result:
			if media['type'] == 'movie':
				print('		Updated')
			elif media['type'] == 'episode':
				print('			Updated')
		result_json.append(media["ratingKey"])

	return result_json


if __name__ == '__main__':
	from argparse import ArgumentParser

	from requests import Session

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

	# Setup arg parsing
	parser = ArgumentParser(description="Change the audio/subtitle track, based on target language, forced status, codec, title strings and/or channel count (audio) for a movie/episode up to all movie/show libraries.")
	parser.add_argument('-t', '--Type', choices=TrackType._member_names_, required=True, help="Give the type of stream to change")

	ps = parser.add_argument_group(title="Preference Settings")
	ps.add_argument('-L', '--Language', type=str, action='append', required=True, help="ISO-639-1 language code (2 lowercase letters e.g. 'en') to try to set the stream to; give multiple times to setup a preference order")
	ps.add_argument('-f', '--Forced', choices=['avoid', 'prefer'], default='avoid', help='How forced streams should be treated; default is "avoid"')
	ps.add_argument('-c', '--Codec', type=str, action='append', default=[], help="Name of stream codec to prefer; give multiple times to setup a preference order")
	ps.add_argument('-T', '--TitleContains', type=str, action='append', default=[], help="Give preference to streams that have the given value in their title")
	ps.add_argument('-C', '--ChannelCount', type=int, default=None, help="AUDIO ONLY: Give preference to streams that have the given amount of audio channels")

	ts = parser.add_argument_group(title="Target Selectors")
	ts.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	ts.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	ts.add_argument('--AllShow', action='store_true', help='Target all show libraries')

	ts.add_argument('-l', '--LibraryName', type=str, action='append', help="Name of target library; allowed to give argument multiple times")
	ts.add_argument('-m', '--MovieName', type=str, action='append', default=[], help="Target a specific movie inside a movie library based on it's name; allowed to give argument multiple times")
	ts.add_argument('-s', '--SeriesName', type=str, action='append', default=[], help="Target a specific series inside a show library based on it's name")
	ts.add_argument('-S', '--SeasonNumber', type=int, action='append', default=[], help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given exactly once) (specials is 0); allowed to give argument multiple times")
	ts.add_argument('-e', '--EpisodeNumber', type=int, action='append', default=[], help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given exactly once); allowed to give argument multiple times")
	ts.add_argument('-u', '--User', type=str, action='append', default=['@me'], help="Select the user(s) to apply this script to; Give username, '@me' for yourself or '@all' for everyone; allowed to give argument multiple times")

	args = parser.parse_args()

	try:
		lf = LibraryFilter(
			all=args.All,
			all_movie=args.AllMovie,
			all_show=args.AllShow,
			libraries=args.LibraryName,
			movies=args.MovieName,
			series=args.SeriesName,
			season_numbers=args.SeasonNumber,
			episode_numbers=args.EpisodeNumber
		)

		sf = StreamFilter(
			language=args.Language,
			prefer_forced=args.Forced == 'prefer',
			codec=args.Codec,
			title_contains=args.TitleContains,
			channel_count=args.ChannelCount
		)

	except ValueError as e:
		parser.error(e.args[0])

	audio_sub_changer(
		ssn,
		lf, TrackType[args.Type], sf,
		users=args.User
	)
