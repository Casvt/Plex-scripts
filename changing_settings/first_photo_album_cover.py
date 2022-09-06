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

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

#keeps track of covers of albums including new covers
album_images = {}

def _process_album(ssn, album_key: str):
	album_image = ''

	album_output = ssn.get(f'{base_url}{album_key}').json()['MediaContainer']['Metadata']
	#if there are sub-albums, do them first but also note first picture in album
	for image in album_output:
		if not 'Media' in image.keys():
			_process_album(image['key'])
		elif not album_image:
			album_image = image

	if album_image:
		#there is a picture present in the album, make it the cover
		album_images[album_image['parentRatingKey']] = album_image['Media'][0]['Part'][0]['file']
		ssn.post(f'{base_url}/library/metadata/{album_image["parentRatingKey"]}/posters', data=open(album_image['Media'][0]['Part'][0]['file'], 'rb').read(), headers={})
	else:
		#there isnt a picture in the album so use the cover of the first sub-album
		for image in album_output:
			if not 'Media' in image.keys():
				album_images[image['parentRatingKey']] = album_images[image['ratingKey']]
				ssn.post(f'{base_url}/library/metadata/{image["parentRatingKey"]}/posters', data=open(album_images[image['ratingKey']], 'rb').read(), headers={})
				break

def first_photo_album_cover(ssn, library_name: str, exclude_name: list=[], exclude_regex: list=[], include_name: list=[], include_regex: list=[]):
	result_json = []

	#check for illegal argument parsing
	if include_name: exclude_name = []
	if include_regex: exclude_regex = []

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] != library_name: continue

		#this library is targeted
		print(lib['title'])
		if lib['type'] == 'photo':
			lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer']['Metadata']
			#loop through every album in the library
			for album in lib_output:
				#check if album is allowed to be processed
				if include_name and album['title'] not in include_name: continue
				if exclude_name and album['title'] in exclude_name: continue
				if include_regex:
					for regex in include_regex:
						if re_match(regex, album['title']):
							break
					else: continue
				if exclude_regex:
					skip_album = False
					for regex in exclude_regex:
						if re_match(regex, album['title']):
							skip_album = True
							break
					if skip_album == True: continue

				#process album
				print(f'	{album["title"]}')
				_process_album(ssn, album['key'])
				result_json.append(album['key'])
		else:
			return 'Library not supported'

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	#setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = ArgumentParser(description='Set the first image of an album as the album cover')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library', required=True)
	parser.add_argument('-e','--ExcludeName', type=str, help='Give name of album to exclude from processing; allowed to give argument multiple times', action='append', default=[])
	parser.add_argument('-E','--ExcludeRegex', type=str, help='Give regex where matching album names are excluded from processing; allowed to give argument multiple times', action='append')
	parser.add_argument('-i','--IncludeName', type=str, help='Give name of album to only process; overrides -e/--ExcludeName; allowed to give argument multiple times', action='append', default=[])
	parser.add_argument('-I','--IncludeRegex', type=str, help='Give regex where only matching albums are processed; overrides -E/--ExcludeRegex; allowed to give argument multiple times', action='append', default=[])

	args = parser.parse_args()
	#call function and process result
	response = first_photo_album_cover(ssn=ssn, library_name=args.LibraryName, exclude_name=args.ExcludeName, exclude_regex=args.ExcludeRegex, include_name=args.IncludeName, include_regex=args.IncludeRegex)
	if not isinstance(response, list):
		parser.error(response)
