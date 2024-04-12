#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Export plex posters to external files or import external files into plex
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from os.path import dirname, isfile, join
from typing import List, Union

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

types = ('export','import')

def _export(type: str, data: dict, ssn, process: list, poster_name: str, background_name: str) -> Union[str, None]:
	# Determine in which folder to put the file(s)
	if type in ('movie','episode'):
		file_path: str = dirname(data['Media'][0]['Part'][0]['file'])
	elif type in ('show','artist'):
		file_path: str = data['Location'][0]['path']
	elif type in ('season','album'):
		season_output: List[dict] = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		file_path: str = dirname(season_output[0]['Media'][0]['Part'][0]['file'])

	if 'poster' in process and 'thumb' in data:
		# Export poster
		poster_data: bytes = ssn.get(f'{base_url}{data["thumb"]}').content
		poster_path = join(file_path, f'{poster_name}.jpg')

		# Write to file
		try:
			with open(poster_path, 'wb') as f:
				f.write(poster_data)
		except OSError:
			return f'Failed to write to file: {poster_path}'

	if 'background' in process and 'art' in data:
		# Export background (aka art)
		background_data: bytes = ssn.get(f'{base_url}{data["art"]}').content
		background_path = join(file_path, f'{background_name}.jpg')

		# Write to file
		try:
			with open(background_path, 'wb') as f:
				f.write(background_data)
		except OSError:
			return f'Failed to write to file: {background_path}'

	return

def _import(type: str, data: dict, ssn, process: list, poster_name: str, background_name: str) -> Union[str, None]:
	# Determine in which folder the file(s) should be
	if type in ('movie','episode'):
		file_path: str = dirname(data['Media'][0]['Part'][0]['file'])
	elif type in ('show','artist'):
		file_path: str = data['Location'][0]['path']
	elif type in ('season','album'):
		season_output: List[dict] = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		file_path: str = dirname(season_output[0]['Media'][0]['Part'][0]['file'])

	poster_path = join(file_path, f'{poster_name}.jpg')
	if 'poster' in process and isfile(poster_path):
		# Import poster
		try:
			with open(poster_path, 'rb') as f:
				poster_data = f.read()
		except OSError:
			return f'Failed to read file: {poster_path}'
		ssn.post(f'{base_url}/library/metadata/{data["ratingKey"]}/posters', data=poster_data)

	background_path = join(file_path, f'{background_name}.jpg')
	if 'background' in process and isfile(background_path):
		# Import background (aka art)
		try:
			with open(background_path, 'rb') as f:
				background_data = f.read()
		except OSError:
			return f'Failed to read file: {background_path}'
		ssn.post(f'{base_url}/library/metadata/{data["ratingKey"]}/arts', data=background_data)

	return

def poster_exporter_importer(
	ssn, type: str, process: list,
	all: bool, all_movie: bool=False, all_show: bool=False, all_music: bool=False,
	library_name: str=None,
	movie_name: str=None,
	series_name: str=None, season_number: int=None, episode_number: int=None,
	artist_name: str=None, album_name: str=None,
	no_episode_poster: bool=False,
	poster_name: str='poster', background_name: str='background'
) -> List[int]:
	result_json = []
	lib_target_specifiers = (library_name,movie_name,series_name,season_number,episode_number,artist_name,album_name)
	all_target_specifiers = (all_movie, all_show, all_music)

	# Check for illegal arg parsing
	if not type in types:
		return 'Invalid value for "type"'

	if all:
		if lib_target_specifiers.count(None) < len(lib_target_specifiers) or True in all_target_specifiers:
			return 'Both "all" and a target-specifier are set'

	else:
		if not True in all_target_specifiers and library_name is None:
			return '"all" is set to False but no target-specifier is given'
		if season_number is not None and series_name is None:
			return '"season_number" is set but not "series_name"'
		if episode_number is not None and (season_number is None or series_name is None):
			return '"episode_number" is set but not "season_number" or "series_name"'
		if album_name is not None and artist_name is None:
			return '"album_name" is set but not "artist_name"'

	args = {
		'ssn': ssn,
		'process': process,
		'poster_name': poster_name,
		'background_name': background_name
	}
	if type == 'export':
		method = _export
	elif type == 'import':
		method = _import

	sections: List[dict] = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
	for lib in sections:
		if not (
			lib['type'] in ('movie','show','artist')
			and (all
				or (library_name is not None and lib['title'] == library_name)
				or (all_movie and lib['type'] == 'movie')
				or (all_show and lib['type'] == 'show')
				or (all_music and lib['type'] == 'artist')
			)
		):
			continue

		# This library (or something in it) should be processed
		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all')
		if lib_output.status_code != 200: continue
		lib_output: List[dict] = lib_output.json()['MediaContainer'].get('Metadata',[])

		if lib['type'] == 'movie':
			for movie in lib_output:
				if movie_name is not None and movie['title'] != movie_name:
					continue

				response = method(type='movie', data=movie, **args)
				if isinstance(response, str): return response
				result_json.append(movie['ratingKey'])

				if movie_name is not None:
					break
			else:
				if movie_name is not None:
					return 'Movie not found'

		elif lib['type'] == 'show':
			for show in lib_output:
				if series_name is not None and show['title'] != series_name:
					continue

				# Process show
				show_info: dict = ssn.get(
					f'{base_url}/library/metadata/{show["ratingKey"]}'
				).json()['MediaContainer']['Metadata'][0]
				response = method(type='show', data=show_info, **args)
				if isinstance(response, str): return response
				result_json.append(show['ratingKey'])

				# Process seasons
				season_info = ssn.get(f'{base_url}{show["key"]}')
				if season_info.status_code != 200: continue
				season_info: List[dict] = season_info.json()['MediaContainer']['Metadata']
				for season in season_info:
					if season_number is not None and season['index'] != season_number:
						continue

					response = method(type='season', data=season, **args)
					if isinstance(response, str): return response
					result_json.append(season['ratingKey'])

					if season_number is not None:
						break
				else:
					if season_number is not None:
						return 'Season not found'

				# Process episodes
				if not no_episode_poster:
					episode_info: List[dict] = ssn.get(
						f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves'
					).json()['MediaContainer']['Metadata']
					for episode in episode_info:
						if season_number is not None and episode['parentIndex'] != season_number:
							continue
						if episode_number is not None and episode['index'] != episode_number:
							continue

						response = method(type='episode', data=episode, **args)
						if isinstance(response, str): return response
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

		elif lib['type'] == 'artist':
			for artist in lib_output:
				if artist_name is not None and artist['title'] != artist_name:
					continue

				# Process artist
				artist_info: dict = ssn.get(
					f'{base_url}/library/metadata/{artist["ratingKey"]}'
				).json()['MediaContainer']['Metadata'][0]
				response = method(type='artist', data=artist_info, **args)
				if isinstance(response, str): return response
				result_json.append(artist['ratingKey'])

				# Process albums
				album_info = ssn.get(f'{base_url}{artist["key"]}')
				if album_info.status_code != 200: continue
				album_info: List[dict] = album_info.json()['MediaContainer'].get('Metadata',[])
				for album in album_info:
					if album_name is not None and album['title'] != album_name:
						continue

					response = method(type='album', data=album, **args)
					if isinstance(response, str): return response
					result_json.append(album['ratingKey'])

					if album_name is not None:
						break
				else:
					if album_name is not None:
						return 'Album not found'

				if artist_name is not None:
					break
			else:
				if artist_name is not None:
					return 'Artist not found'

		else:
			print('	Library not supported')

		if library_name is not None:
			break
	else:
		if library_name is not None:
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
	parser = ArgumentParser(description='Export plex posters to external files or import external files into plex')
	parser.add_argument('-t','--Type', help='Export plex images to files or import files to plex', choices=types, required=True)
	parser.add_argument('-p','--Process', action='append', help='The type of images that should be processed', choices=['poster','background'], required=True)
	parser.add_argument('-E','--NoEpisodePoster', action='store_true', help='Don\'t target episodes (e.g. when selecting a complete series, only target the series and season posters)')
	parser.add_argument('-P','--PosterName', type=str, help='The name of the poster file to search for (importing) or export to (exporting). Default is "poster"', default='poster')
	parser.add_argument('-B','--BackgroundName', type=str, help='The name of the background file to search for (importing) or export to (exporting). Default is "background"', default='background')

	# Args regarding target selection
	# General selectors
	parser.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	parser.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	parser.add_argument('--AllShow', action='store_true', help='Target all show libraries')
	parser.add_argument('--AllMusic', action='store_true', help='Target all music libraries')
	parser.add_argument('-l','--LibraryName', type=str, help='Target a specific library based on it\'s name (movie, show and music libraries supported)')
	# Movie selectors
	parser.add_argument('-m','--MovieName', type=str, help='Target a specific movie inside a movie library based on it\'s name (only accepted when -l is a movie library)', default='')
	# Show selectors
	parser.add_argument('-s','--SeriesName', type=str, help='Target a specific series inside a show library based on it\'s name (only accepted when -l is a show library)')
	parser.add_argument('-S','--SeasonNumber', type=int, help='Target a specific season inside the targeted series based on it\'s number (only accepted when -s is given) (specials is 0)')
	parser.add_argument('-e','--EpisodeNumber', type=int, help='Target a specific episode inside the targeted season based on it\'s number (only accepted when -S is given)')
	# Music selectors
	parser.add_argument('-A','--ArtistName', type=str, help='Target a specific artist inside a music library based on it\'s name (only accepted when -l is a music library)')
	parser.add_argument('-d','--AlbumName', type=str, help='Target a specific album inside the targeted artist based on it\'s name (only accepted when -A is given)')

	args = parser.parse_args()
	# Call function and process result
	response = poster_exporter_importer(
		ssn=ssn, type=args.Type, process=args.Process,
		all=args.All, all_movie=args.AllMovie, all_show=args.AllShow, all_music=args.AllMusic,
		library_name=args.LibraryName,
		movie_name=args.MovieName,
		series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber,
		artist_name=args.ArtistName, album_name=args.AlbumName,
		no_episode_poster=args.NoEpisodePoster,
		poster_name=args.PosterName, background_name=args.BackgroundName
	)
	if not isinstance(response, list):
		if response == 'Both "all" and a target-specifier are set':
			parser.error('Both -a/--All and a target-specifier are set')
		elif response == '"all" is set to False but no target-specifier is given':
			parser.error('-a/--All is not set but also no target-specifier is set')
		elif response == '"season_number" is set but not "series_name"':
			parser.error('-S/--SeasonNumber is set but not -s/--SeriesName')
		elif response == '"episode_number" is set but not "season_number" or "series_name"':
			parser.error('-e/--EpisodeNumber is set but not -S/--SeasonNumber or -s/--SeriesName')
		else:
			parser.error(response)
