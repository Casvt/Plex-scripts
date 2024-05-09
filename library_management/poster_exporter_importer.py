#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Export plex posters to external files or import external files into plex.

Requirements (python3 -m pip install [requirement]):
	requests

Setup:
	1. Fill the variables below.
	2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
		python3 poster_exporter_importer.py -h
		or
		python poster_exporter_importer.py -h

Examples:
	-t export -p poster -p background -E -l Tv-series -s "Initial D"

		Export the posters and backgrounds (A.K.A. arts), but not of the episodes.
		Do this for the series "Initial D" in the "Tv-series" library.

	-t export -p poster --AllMusic

		Export the poster for all artists, albums and tracks.

	-t import -p poster -l Music -A "Drake" -b "Scorpion" -d 2

		Import the poster files for the tracks on disc 2 of Drake's album "Scorpion".
"""

#===== FILL THESE VARIABLES =====
plex_base_url = ''
plex_api_token = ''
#================================

from dataclasses import dataclass, field
from enum import Enum
from os import getenv
from os.path import dirname, isfile, join, splitext
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Tuple, Union

if TYPE_CHECKING:
	from requests import Session

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = plex_base_url.rstrip('/')


class ActionType(Enum):
	EXPORT = 1
	IMPORT = 2


@dataclass
class LibraryFilter:
	all: bool = False
	all_movie: bool = False
	all_show: bool = False
	all_music: bool = False
	libraries: List[str] = field(default_factory=lambda: [])
	movies: List[str] = field(default_factory=lambda: [])
	series: List[str] = field(default_factory=lambda: [])
	season_numbers: List[int] = field(default_factory=lambda: [])
	episode_numbers: List[int] = field(default_factory=lambda: [])
	artists: List[str] = field(default_factory=lambda: [])
	albums: List[str] = field(default_factory=lambda: [])
	discs: List[int] = field(default_factory=lambda: [])
	tracks: List[int] = field(default_factory=lambda: [])

	def __post_init__(self):
		self.content_specifiers = (
			self.libraries,
			self.movies,
			self.series, self.season_numbers, self.episode_numbers,
			self.artists, self.albums, self.discs, self.tracks
		)
		self.lib_specifiers = (
			self.all_movie, self.all_show, self.all_music
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

			if len(self.artists) > 1:
				if self.albums:
					# Albums with multiple artists
					raise ValueError("Can't give albums for multiple artists")

				elif self.discs:
					# Discs with multiple artists
					raise ValueError("Can't give discs for multiple artists")

				elif self.tracks:
					# Tracks with multiple artists
					raise ValueError("Can't give tracks for multiple artists")

			elif len(self.artists) == 1:
				if len(self.albums) > 1:
					if self.discs:
						# Discs with multiple albums
						raise ValueError("Can't give discs for multiple albums")

					elif self.tracks:
						# Tracks with multiple albums
						raise ValueError("Can't give tracks for multiple albums")

				elif len(self.albums) == 1:
					if len(self.discs) > 1 and self.tracks:
						# Tracks with multiple discs
						raise ValueError("Can't give tracks for multiple discs")

					elif not self.discs and self.tracks:
						# Tracks but no discs
						raise ValueError("Can't give tracks without specifying a disc number")

				else:
					if self.discs:
						# Discs but no album
						raise ValueError("Can't give disc numbers without specifying an album")

					elif self.tracks:
						# Tracks but no album
						raise ValueError("Can't give track numbers without specifying an album")

			else:
				if self.albums:
					# Albums but no artist
					raise ValueError("Can't give albums without specifying an artist")

				elif self.discs:
					# Discs but no artist
					raise ValueError("Can't give disc numbers without specifying an artist")

				elif self.tracks:
					# Tracks but no artist
					raise ValueError("Can't give track numbers without specifying an artist")

		return


def _get_library_entries(
	ssn: 'Session',
	library_filter: LibraryFilter
) -> Generator[dict, Any, Any]:
	"""Get library entries to iterate over.

	Args:
		ssn (Session): The `requests.Session` to make the requests with.
		library_filter (LibraryFilter): The filters to apply.

	Yields:
		Generator[dict, Any, Any]: The resulting media information.
	"""
	lf = library_filter

	sections: List[dict] = ssn.get(
		f'{base_url}/library/sections'
	).json()['MediaContainer'].get('Directory', [])

	for lib in sections:
		if not (
			lib['type'] in ('movie', 'show', 'artist')
			and
				lf.all
				or lf.all_movie and lib['type'] == 'movie'
				or lf.all_show and lib['type'] == 'show'
				or lf.all_music and lib['type'] == 'artist'
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

				show_output: dict = ssn.get(
					f'{base_url}/library/metadata/{show["ratingKey"]}',
					params={'includeChildren': 1}
				).json()['MediaContainer'].get('Metadata', [{}])[0]
				if not show_output:
					continue

				print(f'	{show["title"]}')
				yield show_output

				for season in show_output["Children"].get("Metadata", []):
					if lf.season_numbers and not season['index'] in lf.season_numbers:
						continue

					season_output: dict = ssn.get(
						f'{base_url}/library/metadata/{season["ratingKey"]}/children'
					).json()['MediaContainer']
					season_output["type"] = "season"
					season_output["ratingKey"] = season["ratingKey"]

					if not "Metadata" in season_output:
						continue

					print(f'		{season["title"]}')
					yield season_output

					for episode in season_output["Metadata"]:
						if lf.episode_numbers and not episode['index'] in lf.episode_numbers:
							continue

						print(f'			Episode {episode["index"]}')
						yield episode

		elif lib['type'] == 'artist':
			for artist in lib_output:
				if lf.artists and not artist['title'] in lf.artists:
					continue

				artist_output: dict = ssn.get(
					f'{base_url}/library/metadata/{artist["ratingKey"]}',
					params={'includeChildren': 1}
				).json()['MediaContainer'].get('Metadata', [{}])[0]
				if not artist_output:
					continue

				print(f'	{artist["title"]}')
				yield artist_output

				for album in artist_output["Children"].get("Metadata", []):
					if lf.albums and not album['title'] in lf.albums:
						continue

					album_output: dict = ssn.get(
						f'{base_url}/library/metadata/{album["ratingKey"]}/children'
					).json()['MediaContainer']
					album_output["type"] = "album"
					album_output["ratingKey"] = album["ratingKey"]

					if not "Metadata" in album_output:
						continue

					print(f'		{album["title"]}')
					yield album_output

					for track in album_output["Metadata"]:
						if lf.discs and not track["parentIndex"] in lf.discs:
							continue

						if lf.tracks and not track["index"] in lf.tracks:
							continue

						print(f'			Disc {track["parentIndex"]} Track {track["index"]} - {track["title"]}')
						yield track

	return


def _get_poster_bg_paths(
	media: Dict[str, Any],
	poster_name: str,
	background_name: str
) -> Tuple[Union[str, None], Union[str, None]]:
	"""Generate name of poster/background file for media.

	Args:
		media (Dict[str, Any]): The media to generate for.
		poster_name (str): The name of the default poster file.
		background_name (str): The name of the default background file.

	Returns:
		Tuple[Union[str, None], Union[str, None]]: Path to the supposed poster
		file and path to the supposed background file.
	"""
	if media["type"] == "movie":
		folder = dirname(media.get("Media", [{}])[0].get("Part", [{}])[0].get("file", ""))
		if not folder:
			return None, None
		poster_path = join(
			folder,
			f"{poster_name}.jpg"
		)
		bg_path = join(
			folder,
			f"{background_name}.jpg"
		)

	elif media["type"] in ("show", "artist"):
		folder = media["Location"][0]["path"]
		poster_path = join(
			folder,
			f"{poster_name}.jpg"
		)
		bg_path = join(
			folder,
			f"{background_name}.jpg"
		)

	elif media["type"] == "season":
		folder = dirname(media["Metadata"][0].get("Media", [{}])[0].get("Part", [{}])[0].get("file", ""))
		if not folder:
			return None, None
		if media["parentIndex"] == 0:
			poster_path = join(
				folder,
				"season-specials-poster.jpg"
			)
			bg_path = join(
				folder,
				"season-specials-background.jpg"
			)
		else:
			poster_path = join(
				folder,
				f"Season{media['parentIndex']}.jpg"
			)
			bg_path = join(
				folder,
				f"Season{media['parentIndex']}-background.jpg"
			)

	elif media["type"] == "album":
		folder = dirname(media["Metadata"][0].get("Media", [{}])[0].get("Part", [{}])[0].get("file", ""))
		if not folder:
			return None, None
		poster_path = join(
			folder,
			f"{poster_name}.jpg"
		)
		bg_path = join(
			folder,
			f"{background_name}.jpg"
		)

	elif media["type"] in ("episode", "track"):
		file = media.get("Media", [{}])[0].get("Part", [{}])[0].get("file", "")
		if not file:
			return None, None
		poster_path = splitext(file)[0] + '.jpg'
		bg_path = None

	return poster_path, bg_path


def _export(
	ssn: 'Session', media: Dict[str, Any],
	process: List[str],
	poster_name: str, background_name: str
) -> None:
	"""Export the poster of the media to a file.

	Args:
		ssn (Session): The plex requests session to fetch with.
		media (Dict[str, Any]): The media to export for.
		process (List[str]): The image types to export.
		poster_name (str): The default poster name.
		background_name (str): The default background name.
	"""
	poster_path, bg_path = _get_poster_bg_paths(
		media,
		poster_name,
		background_name
	)

	if "poster" in process and poster_path and "thumb" in media:
		try:
			with open(poster_path, "wb") as f, \
			ssn.get(f"{base_url}{media['thumb']}", stream=True) as r:

				for chunk in r.iter_content(chunk_size=100_000): # 100KB chunks
					f.write(chunk)

		except OSError:
			if media["type"] == "track":
				print(f"				Failed to write to file: {poster_path}")
			else:
				print(f"			Failed to write to file: {poster_path}")

	if "background" in process and bg_path and "art" in media:
		try:
			with open(bg_path, "wb") as f, \
			ssn.get(f"{base_url}{media['art']}", stream=True) as r:

				for chunk in r.iter_content(chunk_size=100_000): # 100KB chunks
					f.write(chunk)

		except OSError:
			if media["type"] == "track":
				print(f"				Failed to write to file: {bg_path}")
			else:
				print(f"			Failed to write to file: {bg_path}")

	return


def _import(
	ssn: 'Session', media: Dict[str, Any],
	process: List[str],
	poster_name: str, background_name: str
) -> None:
	"""Import the poster for the media from a file.

	Args:
		ssn (Session): The plex requests session to fetch with.
		media (Dict[str, Any]): The media to import for.
		process (List[str]): The image types to import.
		poster_name (str): The default poster name.
		background_name (str): The default background name.
	"""
	poster_path, bg_path = _get_poster_bg_paths(
		media,
		poster_name,
		background_name
	)

	if "poster" in process and poster_path and isfile(poster_path):
		try:
			with open(poster_path, "rb") as f:
				ssn.post(
					f"{base_url}/library/metadata/{media['ratingKey']}/posters",
					data=f
				)

		except OSError:
			if media["type"] == "track":
				print(f"				Failed to read file: {poster_path}")
			else:
				print(f"			Failed to read file: {poster_path}")

	if "background" in process and bg_path and isfile(bg_path):
		try:
			with open(bg_path, "rb") as f:
				ssn.post(
					f"{base_url}/library/metadata/{media['ratingKey']}/arts",
					data=f
				)

		except OSError:
			if media["type"] == "track":
				print(f"				Failed to read file: {bg_path}")
			else:
				print(f"			Failed to read file: {bg_path}")

	return


def poster_exporter_importer(
	ssn: 'Session', library_filter: LibraryFilter,
	action: ActionType, process: List[str],
	no_episode_poster: bool = False, no_track_poster: bool = False,
	poster_name: str = 'poster', background_name: str = 'background'
) -> List[int]:
	"""Export plex posters to external files or import external files into plex.

	Args:
		ssn (Session): The plex requests session to fetch with.

		library_filter (LibraryFilter): The filter to apply to the media.

		action (ActionType): The type of action to do.

		process (List[str]): What image types to process.

		no_episode_poster (bool, optional): Don't process episodes.
			Defaults to False.

		no_track_poster (bool, optional): Don't process tracks.
			Defaults to False.

		poster_name (str, optional): Name of poster files.
			Defaults to 'poster'.

		background_name (str, optional): Name of background files.
			Defaults to 'background'.

	Returns:
		List[int]: List of media rating keys that were processed.
	"""
	result_json = []

	method = _export if action == ActionType.EXPORT else _import
	for media in _get_library_entries(ssn, library_filter):
		if media["type"] == "episode" and no_episode_poster:
			continue
		if media["type"] == "track" and no_track_poster:
			continue

		method(ssn, media, process, poster_name, background_name)
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
	parser = ArgumentParser(description="Export plex posters to external files or import external files into plex")
	parser.add_argument('-t', '--Type', choices=[m.lower() for m in ActionType._member_names_], required=True, help="Export plex images to files or import files to plex")
	parser.add_argument('-p','--Process', action='append', choices=['poster', 'background'], required=True, help='The type of images that should be processed; allowed to give argument multiple times')
	parser.add_argument('-E','--NoEpisodePoster', action='store_true', help='Don\'t target episodes (e.g. when selecting a complete series, only target the series and season posters)')
	parser.add_argument('-T','--NoTrackPoster', action='store_true', help='Don\'t target tracks (e.g. when selecting a complete album, only target the album poster)')
	parser.add_argument('-P','--PosterName', type=str, default='poster', help='The name of the poster file to search for (importing) or export to (exporting). Default is "poster"')
	parser.add_argument('-B','--BackgroundName', type=str, default='background', help='The name of the background file to search for (importing) or export to (exporting). Default is "background"')

	ts = parser.add_argument_group("Target Selectors")
	ts.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	ts.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	ts.add_argument('--AllShow', action='store_true', help='Target all show libraries')
	ts.add_argument('--AllMusic', action='store_true', help='Target all music libraries')

	ts.add_argument('-l', '--LibraryName', type=str, action='append', default=[], help="Name of target library; allowed to give argument multiple times")
	ts.add_argument('-m', '--MovieName', type=str, action='append', default=[], help="Target a specific movie inside a movie library based on it's name; allowed to give argument multiple times")
	ts.add_argument('-s', '--SeriesName', type=str, action='append', default=[], help="Target a specific series inside a show library based on it's name; allowed to give argument multiple times")
	ts.add_argument('-S', '--SeasonNumber', type=int, action='append', default=[], help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given exactly once) (specials is 0); allowed to give argument multiple times")
	ts.add_argument('-e', '--EpisodeNumber', type=int, action='append', default=[], help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given exactly once); allowed to give argument multiple times")
	ts.add_argument('-A', '--ArtistName', type=str, action='append', default=[], help="Target a specific artist inside a music library based on their name; allowed to give argument multiple times")
	ts.add_argument('-b', '--AlbumName', type=str, action='append', default=[], help="Target a specific album from the targeted artist based on it's name (only accepted when -A is given exactly once); allowed to give argument multiple times")
	ts.add_argument('-d', '--DiscNumber', type=int, action='append', default=[], help="Target a specific disc from the targeted album based on it's number. Most of the time, it's value should be '1'. (only accepted when -b is given exactly once); allowed to give argument multiple times")
	ts.add_argument('-n', '--TrackNumber', type=int, action='append', default=[], help="Target a specific track from the targeted disc based on it's number (only accepted when -d is given exactly once); allowed to give argument multiple times")

	args = parser.parse_args()

	try:
		lf = LibraryFilter(
			all=args.All,
			all_movie=args.AllMovie,
			all_show=args.AllShow,
			all_music=args.AllMusic,
			libraries=args.LibraryName,
			movies=args.MovieName,
			series=args.SeriesName,
			season_numbers=args.SeasonNumber,
			episode_numbers=args.EpisodeNumber,
			artists=args.ArtistName,
			albums=args.AlbumName,
			discs=args.DiscNumber,
			tracks=args.TrackNumber
		)

	except ValueError as e:
		parser.error(e.args[0])

	poster_exporter_importer(
		ssn, lf,
		ActionType[args.Type.upper()], args.Process,
		args.NoEpisodePoster, args.NoTrackPoster,
		args.PosterName, args.BackgroundName
	)
