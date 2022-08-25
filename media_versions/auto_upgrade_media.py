#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Up- or downgrade media if it falls under the defined rules
	Radarr: script will change quality profile of movie and initiate search for it
	Sonarr: script will change quality profile of series, initiate search for episodes and change quality profile of series back
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

triggers = {
	#Define when to up- or downgrade media
	#Give -1 to never go to that resolution/don't use trigger
	#If you have multiple triggers setup, there is an AND correlation between them:
	#	That means that all triggers for a resolution must match in order for media to go to that resolution
	#	So you have to remove some of the triggers below to set it up how you want it
	'days_not_watched': {
		'480': 1095, #1095 (3 years) days ago watched -> 480p
		'720': 365, #365-1094 days ago watched -> 720p
		'1080': 40, #40-364 days ago watched -> 1080p
		'4k': 0 #0-39 days ago watched -> 4k
	},
	'viewcount': {
		'480': -1,
		'720': 1, #0-2 times watched -> 720p
		'1080': 3, #3-4 times watched -> 1080p
		'4k': 5 #5+ times watched -> 4k
	},
	'inverted_viewcount': {
		'480': -1,
		'720': -1,
		'1080': 1, #1+ times watched -> 1080p
		'4k': 0 #0 times watched -> 4k
	}
}

use_radarr = True
radarr_ip = ''
radarr_port = ''
radarr_api_token = ''
radarr_config = {
	#define desired applied radarr profile for each resolution
	#leave a value empty to not up- or downgrade any further
	'480': '',
	'720': '',
	'1080': '',
	'4k': ''
}

use_sonarr = True
sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''
sonarr_config = {
	#define desired applied sonarr profile for each resolution
	#leave a value empty to not up- or downgrade any further
	'480': '',
	'720': '',
	'1080': '',
	'4k': ''
}

from os import getenv
from time import time

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
plex_base_url = f"http://{plex_ip}:{plex_port}"
triggers = getenv('triggers', triggers)
radarr_ip = getenv('radarr_ip', radarr_ip)
radarr_port = getenv('radarr_port', radarr_port)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)
radarr_config = getenv('radarr_config', radarr_config)
use_radarr = getenv('use_radarr', use_radarr)
radarr_base_url = f'http://{radarr_ip}:{radarr_port}/api/v3'
sonarr_ip = getenv('sonarr_ip', sonarr_ip)
sonarr_port = getenv('sonarr_port', sonarr_port)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
sonarr_config = getenv('sonarr_config', sonarr_config)
use_sonarr = getenv('use_sonarr', use_sonarr)
sonarr_base_url = f'http://{sonarr_ip}:{sonarr_port}/api/v3'

resolutions = ('480','720','1080','4k')
radarr_movies = None
radarr_profiles = None
sonarr_profiles = None
sonarr_series = {}

def _change_media(type: str, data: dict, desired_resolution: str, radarr_ssn, sonarr_ssn):
	global radarr_movies, radarr_profiles, sonarr_profiles, sonarr_series

	filepath_current_file = data.get('Media',({}))[0].get('Part',({}))[0].get('file')
	if filepath_current_file == None: return

	if type == 'movie':
		print(f'	Setting {data["title"]} ({data["year"]} to {desired_resolution}')

		if radarr_movies == None:
			radarr_movies = radarr_ssn.get(f'{radarr_base_url}/movie').json()
		if radarr_profiles == None:
			radarr_profiles = radarr_ssn.get(f'{radarr_base_url}/qualityprofile').json()

		#find movie in radarr
		for movie in radarr_movies:
			if movie.get('movieFile',{}).get('path') == filepath_current_file:
				movie_id = movie['id']
				break
		else:
			#movie not found in radarr
			return

		#find id of quality profile in radarr
		for profile in radarr_profiles:
			if profile['name'] == radarr_config.get(desired_resolution):
				profile_id = profile['id']
				break
		else:
			#quality profile not found in radarr
			return

		radarr_ssn.put(f'{radarr_base_url}/movie/editor', json={'movieIds': [movie_id], 'qualityProfileId': profile_id})
		radarr_ssn.post(f'{radarr_base_url}/command', json={'movieIds': [movie_id], 'name': 'MoviesSearch'})

	elif type == 'episode':
		print(f'	Setting {data["grandparentTitle"]} - S{data["parentIndex"]}E{data["index"]} - {data["title"]} to {desired_resolution}')

		if sonarr_profiles == None:
			sonarr_profiles = sonarr_ssn.get(f'{sonarr_base_url}/qualityprofile').json()

		#find episode in sonarr
		episode_search = next(iter(sonarr_ssn.get(f'{sonarr_base_url}/parse', params={'path': filepath_current_file}).json().get('episodes',[])), None)
		if episode_search == None:
			#episode not found in radarr
			return
		series_id = episode_search['seriesId']

		if not series_id in sonarr_series:
			sonarr_series[series_id] = sonarr_ssn.get(f'{sonarr_base_url}/series/{series_id}').json()

		#find id of quality profile in sonarr
		for profile in sonarr_profiles:
			if profile['name'] == sonarr_config.get(desired_resolution):
				profile_id = profile['id']
				break
		else:
			#quality profile not found in sonarr
			return

		current_quality_profile = sonarr_series[series_id]['qualityProfileId']
		sonarr_series[series_id]['qualityProfileId'] = profile_id
		sonarr_ssn.put(f'{sonarr_base_url}/series/{series_id}', json=sonarr_series[series_id], params={'apikey': sonarr_api_token})
		sonarr_ssn.post(f'{sonarr_base_url}/command', json={'name': 'EpisodeSearch', 'episodeIds': [episode_search['id']]})
		sonarr_series[series_id]['qualityProfileId'] = current_quality_profile
		sonarr_ssn.put(f'{sonarr_base_url}/series/{series_id}', json=sonarr_series[series_id], params={'apikey': sonarr_api_token})

	return

def _process_media(type: str, data: dict, radarr_ssn, sonarr_ssn):
	if type == 'movie' and use_radarr == False: return
	if type == 'episode' and use_sonarr == False: return

	current_time = time()
	desired_resolutions = set()
	days_not_watched = (current_time - data.get('lastViewedAt',current_time + 1)) / 86400
	viewcount = data.get('viewCount',0)

	if 'days_not_watched' in triggers and days_not_watched >= 0:
		for resolution in resolutions:
			days = triggers.get('days_not_watched',{}).get(resolution, -1)
			if days == -1: continue
			if days_not_watched >= days:
				#found desired resolution based on days_not_watched
				desired_resolutions.add(resolution)
				break

	if 'viewcount' in triggers:
		for resolution in reversed(resolutions):
			views = triggers.get('viewcount',{}).get(resolution, -1)
			if views == -1: continue
			if viewcount >= views:
				#found desired resolution based on viewcount
				desired_resolutions.add(resolution)
				break

	if 'inverted_viewcount' in triggers:
		for resolution in resolutions:
			views = triggers.get('inverted_viewcount',{}).get(resolution, -1)
			if views == -1: continue
			if viewcount >= views:
				#found desired resolution based on inverted_viewcount
				desired_resolutions.add(resolution)
				break

	if len(desired_resolutions) == 1 \
	and data.get('Media',({}))[0].get('videoResolution') != desired_resolutions[0] \
	and ( \
		(type == 'movie' and radarr_config.get(desired_resolutions[0], '') != '') \
		or (type == 'episode' and sonarr_config.get(desired_resolutions[0], '') != '') \
	):
		#up- or downgrade media
		_change_media(type=type, data=data,desired_resolution=desired_resolutions[0], radarr_ssn=radarr_ssn, sonarr_ssn=sonarr_ssn)

	return

def auto_upgrade_media(
	plex_ssn, radarr_ssn, sonarr_ssn,
	all: bool, all_movie: bool=False, all_show: bool=False,
	library_name: str=None,
	movie_name: str=None,
	series_name: str=None, season_number: int=None, episode_number: int=None
):
	result_json = []
	lib_target_specifiers = (library_name,movie_name,series_name,season_number,episode_number)
	all_target_specifiers = (all_movie, all_show)

	#check for illegal arg parsing
	if use_sonarr == False and use_radarr == False:
		return 'Both sonarr and radarr are disabled'
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

	args = {
		'radarr_ssn': radarr_ssn,
		'sonarr_ssn': sonarr_ssn
	}
	sections = plex_ssn.get(f'{plex_base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
	for lib in sections:
		if not (lib['type'] in ('movie','show','artist') and (all == True \
		or (library_name != None and lib['title'] == library_name) \
		or (all_movie == True and lib['type'] == 'movie') \
		or (all_show == True and lib['type'] == 'show'))):
			#a specific library is targeted and this one is not it, so skip
			continue

		#this library (or something in it) should be processed
		print(lib['title'])

		if lib['type'] == 'movie':
			lib_output = plex_ssn.get(f'{plex_base_url}/library/sections/{lib["key"]}/all')
			if lib_output.status_code != 200: continue
			lib_output = lib_output.json()['MediaContainer'].get('Metadata',[])
			for movie in lib_output:
				if movie_name != None and movie['title'] != movie_name:
					continue

				response = _process_media(type='movie', data=movie, **args)
				if isinstance(response, str): return response
				else: result_json.append(movie['ratingKey'])

				if movie_name != None:
					break
			else:
				if movie_name != None:
					return 'Movie not found'

		elif lib['type'] == 'show':
			lib_output = plex_ssn.get(f'{plex_base_url}/library/sections/{lib["key"]}/all', params={'type': '4'})
			if lib_output.status_code != 200: continue
			lib_output = lib_output.json()['MediaContainer'].get('Metadata',[])
			series_found, season_found = False, False
			for episode in lib_output:
				if series_name != None and episode['grandparentTitle'] != series_name:
					continue
				else:
					series_found = True
				if season_number != None and episode['parentIndex'] != season_number:
					continue
				else:
					series_found = True
				if episode_number != None and episode['index'] != episode_number:
					continue
				if series_name == None:
					series_found = True
				if season_number == None:
					season_found = True

				#process episode
				response = _process_media(type='episode', data=episode, **args)
				if isinstance(response, str): return response
				else: result_json.append(episode['ratingKey'])

				if episode_number != None:
					break
			else:
				if episode_number != None:
					return 'Episode not found'
				if season_found == False:
					return 'Season not found'
				if series_found == False:
					return 'Series not found'

		else:
			print('	Library not supported')

		if library_name != None:
			break
	else:
		if library_name != None:
			return 'Library not found'

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	#setup vars
	plex_ssn = Session()
	plex_ssn.headers.update({'Accept': 'application/json'})
	plex_ssn.params.update({'X-Plex-Token': plex_api_token})
	radarr_ssn = Session()
	radarr_ssn.params.update({'apikey': radarr_api_token})
	sonarr_ssn = Session()
	sonarr_ssn.params.update({'apikey': sonarr_api_token})

	#setup arg parsing
	parser = ArgumentParser(description='Up- or downgrade media if it falls under the defined rules')

	#args regarding target selection
	#general selectors
	parser.add_argument('-a','--All', action='store_true', help='Target every media item in every library (use with care!)')
	parser.add_argument('--AllMovie', action='store_true', help='Target all movie libraries')
	parser.add_argument('--AllShow', action='store_true', help='Target all show libraries')
	parser.add_argument('-l','--LibraryName', type=str, help='Target a specific library based on it\'s name (movie, show and music libraries supported)')
	#movie selectors
	parser.add_argument('-m','--MovieName', type=str, help='Target a specific movie inside a movie library based on it\'s name (only accepted when -l is a movie library)')
	#show selectors
	parser.add_argument('-s','--SeriesName', type=str, help='Target a specific series inside a show library based on it\'s name (only accepted when -l is a show library)')
	parser.add_argument('-S','--SeasonNumber', type=int, help='Target a specific season inside the targeted series based on it\'s number (only accepted when -s is given) (specials is 0)')
	parser.add_argument('-e','--EpisodeNumber', type=int, help='Target a specific episode inside the targeted season based on it\'s number (only accepted when -S is given)')

	args = parser.parse_args()
	#call function and process result
	response = auto_upgrade_media(
		plex_ssn, radarr_ssn, sonarr_ssn,
		all=args.All, all_movie=args.AllMovie, all_show=args.AllShow,
		library_name=args.LibraryName,
		movie_name=args.MovieName,
		series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber,
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
