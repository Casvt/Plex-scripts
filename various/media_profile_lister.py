#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	After selecting a library and giving a quality profile (e.g. main 10),
	the script will list all movies/episodes that match that profile.
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests, argparse

base_url = f'http://{plex_ip}:{plex_port}'
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
parser = argparse.ArgumentParser(description="List all movies or episodes that have a certain quality profile")
parser.add_argument('-l','--LibraryName', help="Name of target library", required=True)
parser.add_argument('-p','--Profile', help="Profile of media to show (e.g. 'main 10')", required=True)
args = parser.parse_args()

lib_id = ''
lib_type = ''
section_output = ssn.get(f'{base_url}/library/sections').json()
for lib in section_output['MediaContainer']['Directory']:
	if lib['title'] == args.LibraryName:
		if lib['type'] in ('movie','show'):
			lib_id = lib['key']
			lib_type = lib['type']
			break
		else:
			parser.error('Library is not a show or movie library')
else:
	parser.error('Library not found')

if lib_type == 'movie':
	for movie in ssn.get(f'{base_url}/library/sections/{lib_id}/all').json()['MediaContainer']['Metadata']:
		if 'videoProfile' in movie['Media'][0].keys() and movie['Media'][0]['videoProfile'] == args.Profile:
			print(movie['title'])

elif lib_type == 'show':
	for show in ssn.get(f'{base_url}/library/sections/{lib_id}/all').json()['MediaContainer']['Metadata']:
		for episode in ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']:
			if 'videoProfile' in episode['Media'][0].keys() and episode['Media'][0]['videoProfile'] == args.Profile:
				print(f'{episode["grandparentTitle"]} - S{episode["parentIndex"]}E{episode["index"]} - {episode["title"]}')
