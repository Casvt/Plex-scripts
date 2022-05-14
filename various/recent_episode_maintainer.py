#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	If targeted media falls under certain conditions, delete the file
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
Warning:
	This script deletes media files if they match the rules set by you! I'm not responsible for any loss of data.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from time import time

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"
latest_episodes = {}

def _process_media(ssn, rating_key: str, days_old: int=None, days_added: int=None, recent_episodes: int=None, view_count: int=None):
	media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}').json()['MediaContainer']['Metadata'][0]
	if days_old and 'lastViewedAt' in media_info and media_info['lastViewedAt'] < time() - (days_old * 86400):
#		ssn.delete(f'{base_url}/library/metadata/{rating_key}')
		return f'Removed: Last time watched was more than {days_old} days ago'
	if days_added and media_info['addedAt'] < time() - (days_added * 86400):
		ssn.delete(f'{base_url}/library/metadata/{rating_key}')
		return f'Removed: Added more than {days_added} days ago'
	if view_count and 'viewCount' in media_info and media_info['viewCount'] >= view_count:
		ssn.delete(f'{base_url}/library/metadata/{rating_key}')
		return f'Removed: Watched {view_count} or more times'
	if recent_episodes:
		if media_info['type'] != 'episode':
			return f'Invalid media type for recent_episodes: {media_info["type"]}'
		#get the x latest episodes of the series and cache it
		if not media_info['grandparentRatingKey'] in latest_episodes:
			show_episodes = ssn.get(f'{base_url}/library/metadata/{media_info["grandparentRatingKey"]}/allLeaves').json()['MediaContainer']['Metadata'][recent_episodes * -1:]
			latest_episodes[media_info['grandparentRatingKey']] = [e['ratingKey'] for e in show_episodes]
		#check if media is in this list
		if not media_info['ratingKey'] in latest_episodes[media_info['grandparentRatingKey']]:
			ssn.delete(f'{base_url}/library/metadata/{rating_key}')
			return f'Removed: Not one of the {view_count} latest episodes of the series'
	return

def recent_episode_maintainer(ssn, library_name: str, movie_name: list=[], series_name: str=None, season_number: int=None, episode_number: int=None, days_old: int=None, days_added: int=None, recent_episodes: int=None, view_count: int=None):
	result_json = []

	#check for illegal arg parsing
	if season_number != None and series_name == None:
		#season number given but no series name
		return '"season_number" is set but not "series_name"'
	if episode_number != None and (season_number == None or series_name == None):
		#episode number given but no season number or no series name
		return '"episode_number" is set but not "season_number" or "series_name"'
	if days_old == None and days_added == None and recent_episodes == None and view_count == None:
		#no rules given
		return 'No rules given'

	kwargs = {
		'days_old': days_old,
		'days_added': days_added,
		'recent_episodes': recent_episodes,
		'view_count': view_count
	}
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] != library_name: continue

		#this library is targeted
		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer']['Metadata']
		if lib['type'] == 'movie':
			#library is a movie lib; loop through every movie
			for movie in lib_output:
				if movie_name and not movie['title'] in movie_name:
					#a specific movie is targeted and this one is not it, so skip
					continue

				print(f'	{movie["title"]}')
				result = _process_media(ssn=ssn, rating_key=movie['ratingKey'], **kwargs)
				if isinstance(result, str) and result.startswith('Removed: '):
					print(f'		{result}')
					result_json.append(movie['ratingKey'])
				elif isinstance(result, str):
					return result

				if movie_name:
					#the targeted movie was found and processed so exit loop
					break

		elif lib['type'] == 'show':
			#library is show lib; loop through every show
			for show in lib_output:
				if series_name != None and show['title'] != series_name:
					#a specific show is targeted and this one is not it, so skip
					continue

				print(f'	{show["title"]}')
				show_output = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']
				#loop through episodes of show to check if targeted season exists
				if season_number != None:
					for episode in show_output:
						if episode['parentIndex'] == season_number:
							break
					else:
						return 'Season not found'
				#loop through episodes of show
				for episode in show_output:
					if season_number != None and episode['parentIndex'] != season_number:
						#a specific season is targeted and this one is not it; so skip
						continue

					if episode_number != None and episode['index'] != episode_number:
						#this season is targeted but this episode is not; so skip
						continue

					print(f'		S{episode["parentIndex"]}E{episode["index"]}	- {episode["title"]}')
					result = _process_media(ssn=ssn, rating_key=episode['ratingKey'], **kwargs)
					if isinstance(result, str) and result.startswith('Removed: '):
						print(f'			{result}')
						result_json.append(episode['ratingKey'])
					elif isinstance(result, str):
						return result

					if episode_number != None:
						#the targeted episode was found and processed so exit loop
						break
				else:
					if episode_number != None:
						#the targeted episode was not found
						return 'Episode not found'

				if series_name != None:
					#the targeted series was found and processed so exit loop
					break
			else:
				if series_name != None:
					#the targeted series was not found
					return 'Series not found'
		else:
			return 'Library not supported'
		#the targeted library was found and processed so exit loop
		break
	else:
		#the targeted library was not found
		return 'Library not found'

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="If targeted media falls under certain conditions, delete the file", epilog="All rules are evaluated as 'or'. So it's [rule 1] or [rule 2] or [rule 3] etc.")
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target library", required=True)
	parser.add_argument('-m', '--MovieName', type=str, help="Target a specific movie inside a movie library based on it's name (only accepted when -l is a movie library); allowed to give argument multiple times", action='append', default=[])
	parser.add_argument('-s', '--SeriesName', type=str, help="Target a specific series inside a show library based on it's name (only accepted when -l is a show library)")
	parser.add_argument('-S', '--SeasonNumber', type=int, help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given) (specials is 0)")
	parser.add_argument('-e', '--EpisodeNumber', type=int, help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given)")
	parser.add_argument('-d', '--DaysOld', type=int, help="Remove media watched later than x days ago for the last time")
	parser.add_argument('-a', '--DaysAdded', type=int, help="Remove media added later than x days ago")
	parser.add_argument('-r', '--RecentEpisodes', type=int, help="Only keep the latest x episodes of a series")
	parser.add_argument('-c', '--ViewCount', type=int, help="Only keep media that has been watched x or less times")

	args = parser.parse_args()
	#call function and process result
	response = recent_episode_maintainer(ssn=ssn, library_name=args.LibraryName, movie_name=args.MovieName, series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber, days_old=args.DaysOld, days_added=args.DaysAdded, recent_episodes=args.RecentEpisodes, view_count=args.ViewCount)
	if not isinstance(response, list):
		if response == '"season_number" is set but not "series_name"':
			parser.error('-S/--SeasonNumber given but not -s/--SeriesName given')

		elif response == '"episode_number" is set but not "season_number" or "series_name"':
			parser.error('-e/--EpisodeNumber given but -S/--SeasonNumber or -s/--SeriesName not given')

		else:
			parser.error(response)
