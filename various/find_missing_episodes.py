#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	List all episodes of a series that are missing
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from re import findall as re_findall
from html import unescape

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def find_missing_episodes(ssn, library_name: str, series_name: str=None, ignore_specials: bool=False):
	result_json, episode_list, show_list = [], [], []

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] != library_name: continue
		if lib['type'] != 'show': return 'Invalid library'

		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'type': '4','includeGuids': '1'}).json()['MediaContainer']['Metadata']

		#check if episodes are allowed
		if series_name:
			lib_output = [e for e in lib_output if e['grandparentTitle'] == series_name]
		if not lib_output:
			return 'Series not found'

		#go through every episode in the library
		for episode in lib_output:
			guids = episode.get('Guid', [])
			for guid in guids:
				if guid['id'].startswith('tvdb://'):
					#episode has tvdb id; note it
					episode_list.append(guid['id'].split('/')[-1])

		#go through every show in the library
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']

		#check if series is allowed
		if series_name:
			lib_output = [s for s in lib_output if s['title'] == series_name]

		for show in lib_output:
			guids = show.get('Guid', [])
			for guid in guids:
				if guid['id'].startswith('tvdb://'):
					#show has tvdb id; note it
					show_list.append([show['title'], guid['id'].split('/')[-1]])
		
		#get episodes of every show on tvdb site and find ones that aren't present in episode_list
		for show in show_list:
			show_info = ssn.get(f'https://thetvdb.com/dereferrer/series/{show[1]}').text
			episode_link = re_findall(r'(?<=<a href=").*?(?=">All Seasons)', show_info)[0]
			show_content = ssn.get(f'https://thetvdb.com{episode_link}').text
			show_ids = [i.split('/')[-1] for i in re_findall(r'<h4 class="list-group-item-heading">(?:.*\n){2}.*?(?=">)', show_content)]
			show_numbers = [n.split('>')[-1].split(' ')[-1].replace('0x','S0E') for n in re_findall(r'<h4 class="list-group-item-heading">(?:.*\n).*?>.*?(?=<)', show_content)]
			show_titles = [unescape(i.split('\n')[-1].strip()) for i in re_findall(r'<h4 class="list-group-item-heading">(?:.*\n){2}.*?">\n.*', show_content)]
			show_episodes = list(zip(show_ids, show_numbers, show_titles))
			for episode in show_episodes:
				if 'S0E' in episode[1]: continue
				if not episode[0] in episode_list:
					print(f'	{show[0]} - {episode[1]} - {episode[2]}')
		break
	else:
		return 'Library not found'

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="List all episodes of a series that are missing")
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target show library", required=True)
	parser.add_argument('-s', '--SeriesName', type=str, help="Target a specific series inside a show library based on it's name")
	parser.add_argument('-i', '--IgnoreSpecials', help="Don't list \"specials\" (season 0) episodes", action='store_true')

	args = parser.parse_args()
	#call function and process result
	response = find_missing_episodes(ssn=ssn, library_name=args.LibraryName, series_name=args.SeriesName, ignore_specials=args.IgnoreSpecials)
	if not isinstance(response, list):
		parser.error(response)
