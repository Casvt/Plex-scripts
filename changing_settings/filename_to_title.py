#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	If a string is present in the filename, add an other string to the plex title
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every 20m or every 12h)
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

mappings = {
	#'filename string': 'plex title string'
	'(en)': '(English)',
}

from os import getenv
from os.path import basename, splitext
from typing import List

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
mappings = getenv('mappings', mappings)
base_url = f"http://{plex_ip}:{plex_port}"
lib_type_mapping = {
	'movie': 1,
	'show': 4
}

def filename_to_title(ssn, mappings: dict, lock_field: bool=True, case_insensitive: bool=True) -> List[int]:
	result_json = []

	if case_insensitive:
		mappings = {k.lower(): v for k, v in mappings.items()}

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
	for lib in sections:
		lib_type = lib_type_mapping.get(lib['type'])
		if not lib_type: continue

		lib_output = ssn.get(
			f'{base_url}/library/sections/{lib["key"]}/all',
			params={'type': lib_type}
		).json()['MediaContainer'].get('Metadata',[])

		for media in lib_output:
			if not 'title' in media: continue
			filename: str = splitext(basename(media['Media'][0]['Part'][0]['file']))[0]
			if case_insensitive:
				filename = filename.lower()
			title: list = media['title'].split(" ")
			
			# Remove current strings and add new ones
			for file_string, title_string in mappings.items():
				try:
					title.remove(title_string)
				except ValueError:
					pass
				if file_string in filename:
					title.append(title_string)

			new_title = " ".join(title)
			if new_title != media['title']:
				# Update title
				result_json.append(media['ratingKey'])
				print(f'{media["title"]} to {new_title}')
				ssn.put(
					f'{base_url}/library/sections/{lib["key"]}/all',
					params={
						'type': lib_type,
						'id': media['ratingKey'],
						'title.value': new_title,
						'title.locked': int(lock_field)
					}
				)

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	# Setup arg parsing
	parser = ArgumentParser(description='If a string is present in the filename, add an other string to the plex title')
	parser.add_argument('-l','--LockField', action='store_true', help='Lock the "title" field in plex after processing the media')
	parser.add_argument('-i','--CaseInsensitive', action='store_true', help='Matching the strings in the filename happens case insensitive')

	args = parser.parse_args()
	# Call function and process result
	response = filename_to_title(ssn=ssn, mappings=mappings, lock_field=args.LockField, case_insensitive=args.CaseInsensitive)
	if not isinstance(response, list):
		parser.error(response)
