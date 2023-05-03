#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	The first image in an album will be made the cover of the album
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every 20m or every 12h)
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from re import match as re_match
from typing import List

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

# Keeps track of covers of albums including new covers
album_images = {}

def _process_album(ssn, album_key: str) -> None:
	album_image = ''

	album_output: List[dict] = ssn.get(f'{base_url}{album_key}').json()['MediaContainer']['Metadata']
	# If there are sub-albums, do them first but also note first picture in album
	for image in album_output:
		if not 'Media' in image:
			_process_album(image['key'])
		elif not album_image:
			album_image = image

	if album_image:
		# There is a picture present in the album, make it the cover
		album_images[album_image['parentRatingKey']] = album_image['Media'][0]['Part'][0]['file']
		with open(album_image['Media'][0]['Part'][0]['file'], 'rb') as f:
			ssn.post(
				f'{base_url}/library/metadata/{album_image["parentRatingKey"]}/posters',
				data=f.read(),
				headers={}
			)
	else:
		# There isn't a picture in the album so use the cover of the first sub-album
		for image in album_output:
			if not 'Media' in image:
				album_images[image['parentRatingKey']] = album_images[image['ratingKey']]
				with open(album_images[image['ratingKey']], 'rb') as f:
					ssn.post(
						f'{base_url}/library/metadata/{image["parentRatingKey"]}/posters',
						data=f.read(),
						headers={}
					)
				break
	return

def first_photo_album_cover(
	ssn, library_name: List[str],
	exclude_name: List[str]=[], exclude_regex: List[str]=[],
	include_name: List[str]=[], include_regex: List[str]=[]
) -> List[int]:
	result_json = []

	# Check for illegal argument parsing
	if include_name: exclude_name = []
	if include_regex: exclude_regex = []

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory', [])
	for lib in sections:
		if not lib['title'] in library_name: continue

		print(lib['title'])
		if lib['type'] == 'photo':
			lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer']['Metadata']
			for album in lib_output:

				# Check if album is allowed to be processed
				if ((include_name and album['title'] not in include_name)
				or (exclude_name and album['title'] in exclude_name)):
					continue

				# All have to not match for the album to be rejected
				if include_regex and all(not re_match(regex, album['title']) for regex in include_regex):
					continue
				# One has to match for the album to be rejected
				if exclude_regex and any(re_match(regex, album['title']) for regex in exclude_regex):
					continue

				# Process album
				print(f'	{album["title"]}')
				_process_album(ssn, album['key'])
				result_json.append(album['key'])
		else:
			return 'Library not supported'

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	# Setup arg parsing
	parser = ArgumentParser(description='Set the first image of an album as the album cover')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library; allowed to give argument multiple times', action='append', required=True)
	parser.add_argument('-e','--ExcludeName', type=str, help='Give name of album to exclude from processing; allowed to give argument multiple times', action='append', default=[])
	parser.add_argument('-E','--ExcludeRegex', type=str, help='Give regex where matching album names are excluded from processing; allowed to give argument multiple times', action='append', default=[])
	parser.add_argument('-i','--IncludeName', type=str, help='Give name of album to only process; overrides -e/--ExcludeName; allowed to give argument multiple times', action='append', default=[])
	parser.add_argument('-I','--IncludeRegex', type=str, help='Give regex where only matching albums are processed; overrides -E/--ExcludeRegex; allowed to give argument multiple times', action='append', default=[])

	args = parser.parse_args()
	# Call function and process result
	response = first_photo_album_cover(
		ssn=ssn, library_name=args.LibraryName,
		exclude_name=args.ExcludeName, exclude_regex=args.ExcludeRegex,
		include_name=args.IncludeName, include_regex=args.IncludeRegex
	)
	if not isinstance(response, list):
		parser.error(response)
