#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Make a playlist with the desired sersies in it and most importantly, in the order that you want:
	sequential, shuffled, semi-shuffled or staggered.
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
To-Do:
	Ability to specify order for playlist but then different order for series or even season
		See https://www.reddit.com/r/PleX/comments/pbwf41/comment/hahjs16/?utm_source=share&utm_medium=web2x&context=3
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import os

# Environmental Variables
plex_ip = os.getenv('plex_ip', plex_ip)
plex_port = os.getenv('plex_port', plex_port)
plex_api_token = os.getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def advanced_playlist(ssn, series_names: list, order: str, playlist_name: str):
	#search for each series that was given

	#episodes list contains episode ratingkeys of all series
	episodes = []
	#series_episodes dict has layout of {series_ratingkey: [episode_ratingkey1, episode_ratingkey2, etc.]}
	series_episodes = {}
	for series in series_names:
		search_results = ssn.get(f'{base_url}/search', params={'query': series}).json()['MediaContainer']
		search_results = search_results['Metadata'] if 'Metadata' in search_results else []
		for search_result in search_results:
			if search_result['title'] == series and search_result['type'] == 'show':
				#series found
				series_output = ssn.get(f'{base_url}/library/metadata/{search_result["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']
				for episode in series_output:
					episodes.append(episode['ratingKey'])

					if search_result['ratingKey'] in series_episodes:
						series_episodes[search_result['ratingKey']].append(episode['ratingKey'])
					else:
						series_episodes[search_result['ratingKey']] = [episode['ratingKey']]
				break
		else:
			#series not found
			return f'The series "{series}" was not found'


	#setup order of episodes of series
	if order == 'sequential':
		#complete series after each other
		pass

	elif order == 'shuffled':
		#random order of all episodes
		import random
		random.shuffle(episodes)
	
	elif order == 'semi-shuffled':
		#series are sequentially ordered but inside the series, the episodes are shuffled
		import random
		episodes = []
		for series in series_episodes.values():
			random.shuffle(series)
			episodes += series
	
	elif order == 'staggered':
		#first episode of each series is added, then the second episode of each series, etc.
		episodes = []
		series_list = list(series_episodes.values())
		range_list = max([len(l) for l in series_list])
		for index in range(range_list):
			for series in series_list:
				try:
					episodes.append(series[index])
				except IndexError:
					pass

	else:
		#unknown order
		return f'The order "{order}" is not recognized'

	#if playlist with this name already exists, remove it first
	playlists = ssn.get(f'{base_url}/playlists').json()['MediaContainer']
	if 'Metadata' in playlists:
		for playlist in playlists['Metadata']:
			if playlist['title'] == playlist_name:
				ssn.delete(f'{base_url}/playlists/{playlist["ratingKey"]}')

	#create playlist
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	ssn.post(f'{base_url}/playlists', params={'type': 'video', 'title': playlist_name, 'smart': '0', 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(episodes)}'})

	return

if __name__ == '__main__':
	import argparse, requests

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept':'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	epilog = """
The orders explained:
	sequential
		The complete series are added after each other
	shuffled
		All episodes of all series are shuffled through each other
	semi-shuffled
		The series are sequential but "inside" the series, the episodes are shuffled
	staggered
		The first episode of each series is added, then the second of each series, etc.
"""

	parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description='Make a playlist with the desired sersies in it and most importantly, in the order that you want: sequential, shuffled, semi-shuffled or staggered', epilog=epilog)
	parser.add_argument('-s','--SeriesName', help='The name of the series that should be in the playlist; argument can be given multiple times for multiple series in the playlist', required=True, action='append', type=str)
	parser.add_argument('-o','--Order', help='The way the series should be ordered in the playlist', required=True, type=str, choices=['sequential', 'shuffled', 'semi-shuffled', 'staggered'])
	parser.add_argument('-n','--PlaylistName', help='The name of the playlist that will be created', required=True, type=str)

	args = parser.parse_args()

	result = advanced_playlist(ssn=ssn, series_names=args.SeriesName, order=args.Order, playlist_name=args.PlaylistName)
	if result != None:
		parser.error(result)