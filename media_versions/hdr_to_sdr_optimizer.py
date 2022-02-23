#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	This script will find any media that has an HDR version but not a SDR version,
	and will put the media in the optimize-queue to make an optimimzed version that is SDR.
	Works with movies and show libraries
Requirements (python3 -m pip install [requirement]):
	PlexAPI
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the argument that you need to give.
To-Do:
	1. Check if media is already in optimize queue and if so don't add again
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests, argparse
from plexapi.server import PlexServer

def checkHDR(media_info):
	for media in media_info['Media']:
		for part in media['Part']:
			for stream in part['Stream']:
				if stream['streamType'] == 1 and 'colorSpace' in stream.keys() and stream['colorSpace'].startswith('bt2020'):
					return 'HDR'
	return 'SDR'

def checkOptimize(media_info):
	print(str(media_info['title']))
	if checkHDR(media_info) == 'SDR': return
	for media in media_info['Media']:
		if 'title' in media.keys() and media['title'].startswith('Optimized for '):
			return 'Not-Converting'
	else:
		print('	Converting')
		plex.fetchItem(media_info['key']).optimize(locationID=-1, targetTagID=2, deviceProfile='Universal TV')
		return 'Converting'

ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
base_url = f'http://{plex_ip}:{plex_port}'
plex = PlexServer(base_url, plex_api_token)

section_output = ssn.get(f'{base_url}/library/sections').json()
parser = argparse.ArgumentParser(description="Script to make an optimized SDR version of HDR media using plex")
parser.add_argument('-l','--LibraryName', help="Name of target library (movie or show library)(allowed to give argument multiple times)", type=str, required=True, action='append')
parser.add_argument('-L','--Limit', help="Don't allow the script to add more that this amount of media to the optimize queue", type=int)
args = parser.parse_args()
lib_ids = []
lib_types = {}
for lib in args.LibraryName:
	for source_lib in section_output['MediaContainer']['Directory']:
		if source_lib['title'] == lib:
			if source_lib['type'] in ('movie','show'):
				lib_ids.append(source_lib['key'])
				lib_types[source_lib['key']] = source_lib['type']
			else:
				print(f'Ignoring the library "{lib}" as it is not a show or movie library')
			break
	else:
		print(f'The library {lib} was not found')

limit = 0
for lib in lib_ids:
	if lib_types[lib] == 'movie':
		for movie in ssn.get(f'{base_url}/library/sections/{lib}/all', params={'hdr': '1'}).json()['MediaContainer']['Metadata']:
			if args.Limit != None and limit == args.Limit:
				print(f'Limit of {args.Limit} reached so stopping script')
				exit(0)
			if checkOptimize(movie) == 'Converting':
				limit += 1

	elif lib_types[lib] == 'show':
		for show in ssn.get(f'{base_url}/library/sections/{lib}/all', params={'episode.hdr': '1'}).json()['MediaContainer']['Metadata']:
			for episode in ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']:
				if args.Limit != None and limit == args.Limit:
					print(f'Limit of {args.Limit} reached so stopping script')
					exit(0)
				episode_output = ssn.get(f'{base_url}/library/metadata/{episode["ratingKey"]}').json()['MediaContainer']['Metadata'][0]
				if checkOptimize(episode_output) == 'Converting':
					limit += 1
