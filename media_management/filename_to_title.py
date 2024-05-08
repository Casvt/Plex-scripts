#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	If a string is present in the filename, add a chosen string to the plex title.

Requirements (python3 -m pip install [requirement]):
	requests

Setup:
	1. Fill the variables below.
	2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
		python3 filename_to_title.py -h
		or
		python filename_to_title.py -h
"""

#===== FILL THESE VARIABLES =====
plex_base_url = ''
plex_api_token = ''

mappings = {
	# 'filename string': 'plex title string'
	'(en)': '(English)',
}
delete_title_string = [] # ['(oopsie)', '(typo)']
add_title_string = [] # ['(always add)', '(processed)']
#================================

from dataclasses import dataclass, field
from os import getenv
from os.path import basename, splitext
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Mapping

if TYPE_CHECKING:
	from requests import Session

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = plex_base_url.rstrip('/')

lib_type_mapping = {
	'movie': 1,
	'episode': 4
}


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
				movie["lib_id"] = lib["key"]
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
					episode["lib_id"] = lib["key"]
					yield episode
	return


def filename_to_title(
	ssn: 'Session', library_filter: LibraryFilter,
	mappings: Mapping[str, str],
	lock_field: bool = False, case_insensitive: bool = False
) -> List[int]:
	"""If a string is present in the filename, add a chosen string to the plex title.

	Args:
		ssn (Session): The plex requests session to fetch with.
		library_filter (LibraryFilter): The filter to apply to the media.
		mappings (Mapping[str, str]): The mapping from filename string to title string.
		lock_field (bool, optional): Lock the "title" field in plex after processing the media.
			Defaults to False.
		case_insensitive (bool, optional): Make the matching of the strings in the filename case insensitive.
			Defaults to False.

	Returns:
		List[int]: List of media rating keys that were edited.
	"""
	result_json = []

	if case_insensitive:
		mappings = {k.lower(): v for k, v in mappings.items()}

	for media in _get_library_entries(ssn, library_filter):
		if not 'title' in media:
			continue

		try:
			filename: str = splitext(basename(media['Media'][0]['Part'][0]['file']))[0]
		except KeyError:
			continue

		if case_insensitive:
			filename = filename.lower()

		title: list = media['title'].split(" ")

		# Remove current strings and add new ones
		for s in (*delete_title_string, *add_title_string, *mappings.values()):
			try:
				title.remove(s)
			except ValueError:
				pass

		add_suffixes = set()
		for file_string, title_string in mappings.items():
			if file_string in filename:
				add_suffixes.add(title_string)

		for s in (*add_title_string, *add_suffixes):
			title.append(s)

		new_title = " ".join(title)
		if new_title != media['title']:
			# Update title
			result_json.append(media['ratingKey'])
			lib_id = media["lib_id"]
			lib_type = lib_type_mapping[media["type"]]
			if media['type'] == 'movie':
				print(f'		{media["title"]} to {new_title}')
			elif media['type'] == 'episode':
				print(f'			{media["title"]} to {new_title}')

			ssn.put(
				f'{base_url}/library/sections/{lib_id}/all',
				params={
					'type': lib_type,
					'id': media['ratingKey'],
					'title.value': new_title,
					'title.locked': int(lock_field)
				}
			)

	return result_json

if __name__ == '__main__':
	from argparse import ArgumentParser

	from requests import Session

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

	# Setup arg parsing
	parser = ArgumentParser(description='If a string is present in the filename, add a chosen string to the plex title.')
	parser.add_argument('-l', '--LockField', action='store_true', help='Lock the "title" field in plex after processing the media')
	parser.add_argument('-i', '--CaseInsensitive', action='store_true', help='Make the matching of the strings in the filename case insensitive')

	ts = parser.add_argument_group(title="Target Selectors")
	ts.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	ts.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	ts.add_argument('--AllShow', action='store_true', help='Target all show libraries')

	ts.add_argument('-l', '--LibraryName', type=str, action='append', help="Name of target library; allowed to give argument multiple times")
	ts.add_argument('-m', '--MovieName', type=str, action='append', default=[], help="Target a specific movie inside a movie library based on it's name; allowed to give argument multiple times")
	ts.add_argument('-s', '--SeriesName', type=str, action='append', default=[], help="Target a specific series inside a show library based on it's name")
	ts.add_argument('-S', '--SeasonNumber', type=int, action='append', default=[], help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given exactly once) (specials is 0); allowed to give argument multiple times")
	ts.add_argument('-e', '--EpisodeNumber', type=int, action='append', default=[], help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given exactly once); allowed to give argument multiple times")

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

	except ValueError as e:
		parser.error(e.args[0])

	filename_to_title(
		ssn, lf, mappings,
		lock_field=args.LockField, case_insensitive=args.CaseInsensitive
	)
