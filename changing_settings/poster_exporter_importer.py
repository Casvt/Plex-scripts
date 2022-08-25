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
from os.path import dirname, join, isfile

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def _export(type: str, data: dict, ssn, process: list, poster_name: str, background_name: str):
	#determine in which folder to put the file(s)
	if type in ('movie','episode'):
		file_path = dirname(data['Media'][0]['Part'][0]['file'])
	elif type in ('show','artist'):
		file_path = data['Location'][0]['path']
	elif type in ('season','album'):
		season_output = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		file_path = dirname(season_output[0]['Media'][0]['Part'][0]['file'])

	if 'poster' in process and data.get('thumb') != None:
		#export poster
		poster_data = ssn.get(f'{base_url}{data["thumb"]}').content
		poster_path = join(file_path, f'{poster_name}.jpg')

		#write to file
		try:
			with open(poster_path, 'wb') as f:
				f.write(poster_data)
		except OSError:
			return f'Failed to write to file: {poster_path}'

	if 'background' in process and data.get('art') != None:
		#export background (aka art)
		background_data = ssn.get(f'{base_url}{data["art"]}').content
		background_path = join(file_path, f'{background_name}.jpg')

		#write to file
		try:
			with open(background_path, 'wb') as f:
				f.write(background_data)
		except OSError:
			return f'Failed to write to file: {background_path}'

	return

def _import(type: str, data: dict, ssn, process: list, poster_name: str, background_name: str):
	#determine in which folder the file(s) should be
	if type in ('movie','episode'):
		file_path = dirname(data['Media'][0]['Part'][0]['file'])
	elif type in ('show','artist'):
		file_path = data['Location'][0]['path']
	elif type in ('season','album'):
		season_output = ssn.get(f'{base_url}{data["key"]}').json()['MediaContainer']['Metadata']
		file_path = dirname(season_output[0]['Media'][0]['Part'][0]['file'])

	poster_path = join(file_path, f'{poster_name}.jpg')
	if 'poster' in process and isfile(poster_path):
		#import poster
		try:
			with open(poster_path, 'rb') as f:
				poster_data = f.read()
		except OSError:
			return f'Failed to read file: {poster_path}'
		ssn.post(f'{base_url}/library/metadata/{data["ratingKey"]}/posters', data=poster_data)

	background_path = join(file_path, f'{background_name}.jpg')
	if 'background' in process and isfile(background_path):
		#import background (aka art)
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
):
	result_json = []
	lib_target_specifiers = (library_name,movie_name,series_name,season_number,episode_number,artist_name,album_name)
	all_target_specifiers = (all_movie, all_show, all_music)

	#check for illegal arg parsing
	if not type in ('export','import'):
		return 'Invalid value for "type"'

	if all == True:
		if lib_target_specifiers.count(None) < len(lib_target_specifiers) or True in all_target_specifiers:
			return 'Both "all" and a target-specifier are set'

	else:
		if not True in all_target_specifiers and library_name == None:
			return '"all" is set to False but no target-specifier is given'
		if season_number != None and series_name == None:
			return '"season_number" is set but not "series_name"'
		if episode_number != None and (season_number == None or series_name == None):
			return '"episode_number" is set but not "season_number" or "series_name"'
		if album_name != None and artist_name == None:
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

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
	for lib in sections:
		if not (lib['type'] in ('movie','show','artist') and (all == True \
		or (library_name != None and lib['title'] == library_name) \
		or (all_movie == True and lib['type'] == 'movie') \
		or (all_show == True and lib['type'] == 'show') \
		or (all_music == True and lib['type'] == 'artist'))):
			#a specific library is targeted and this one is not it, so skip
			continue

		#this library (or something in it) should be processed
		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all')
		if lib_output.status_code != 200: continue
		lib_output = lib_output.json()['MediaContainer'].get('Metadata',[])

		if lib['type'] == 'movie':
			for movie in lib_output:
				if movie_name != None and movie['title'] != movie_name:
					continue

				response = method(type='movie', data=movie, **args)
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

				#process show
				show_info = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}').json()['MediaContainer']['Metadata'][0]
				response = method(type='show', data=show_info, **args)
				if isinstance(response, str): return response
				else: result_json.append(show['ratingKey'])

				#process seasons
				season_info = ssn.get(f'{base_url}{show["key"]}')
				if season_info.status_code != 200: continue
				season_info = season_info.json()['MediaContainer']['Metadata']
				for season in season_info:
					if season_number != None and season['index'] != season_number:
						continue

					response = method(type='season', data=season, **args)
					if isinstance(response, str): return response
					else: result_json.append(season['ratingKey'])

					if season_number != None:
						break
				else:
					if season_number != None:
						return 'Season not found'

				#process episodes
				if no_episode_poster == False:
					episode_info = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']
					for episode in episode_info:
						if season_number != None and episode['parentIndex'] != season_number:
							continue
						if episode_number != None and episode['index'] != episode_number:
							continue

						response = method(type='episode', data=episode, **args)
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

				#process artist
				artist_info = ssn.get(f'{base_url}/library/metadata/{artist["ratingKey"]}').json()['MediaContainer']['Metadata'][0]
				response = method(type='artist', data=artist_info, **args)
				if isinstance(response, str): return response
				else: result_json.append(artist['ratingKey'])

				#process albums
				album_info = ssn.get(f'{base_url}{artist["key"]}')
				if album_info.status_code != 200: continue
				album_info = album_info.json()['MediaContainer'].get('Metadata',[])
				for album in album_info:
					if album_name != None and album['title'] != album_name:
						continue

					response = method(type='album', data=album, **args)
					if isinstance(response, str): return response
					else: result_json.append(album['ratingKey'])

					if album_name != None:
						break
				else:
					if album_name != None:
						return 'Album not found'

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

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Export plex posters to external files or import external files into plex')
	parser.add_argument('-t','--Type', help='Export plex images to files or import files to plex', choices=['export','import'], required=True)
	parser.add_argument('-p','--Process', action='append', help='The type of images that should be processed', choices=['poster','background'], required=True)
	parser.add_argument('-E','--NoEpisodePoster', action='store_true', help='Don\'t target episodes (e.g. when selecting a complete series, only target the series and season posters)')
	parser.add_argument('-P','--PosterName', type=str, help='The name of the poster file to search for (importing) or export to (exporting). Default is "poster"', default='poster')
	parser.add_argument('-B','--BackgroundName', type=str, help='The name of the background file to search for (importing) or export to (exporting). Default is "background"', default='background')

	#args regarding target selection
	#general selectors
	parser.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	parser.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	parser.add_argument('--AllShow', action='store_true', help='Target all show libraries')
	parser.add_argument('--AllMusic', action='store_true', help='Target all music libraries')
	parser.add_argument('-l','--LibraryName', type=str, help='Target a specific library based on it\'s name (movie, show and music libraries supported)')
	#movie selectors
	parser.add_argument('-m','--MovieName', type=str, help='Target a specific movie inside a movie library based on it\'s name (only accepted when -l is a movie library)', default='')
	#show selectors
	parser.add_argument('-s','--SeriesName', type=str, help='Target a specific series inside a show library based on it\'s name (only accepted when -l is a show library)')
	parser.add_argument('-S','--SeasonNumber', type=int, help='Target a specific season inside the targeted series based on it\'s number (only accepted when -s is given) (specials is 0)')
	parser.add_argument('-e','--EpisodeNumber', type=int, help='Target a specific episode inside the targeted season based on it\'s number (only accepted when -S is given)')
	#music selectors
	parser.add_argument('-A','--ArtistName', type=str, help='Target a specific artist inside a music library based on it\'s name (only accepted when -l is a music library)')
	parser.add_argument('-d','--AlbumName', type=str, help='Target a specific album inside the targeted artist based on it\'s name (only accepted when -A is given)')

	args = parser.parse_args()
	#call function and process result
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
