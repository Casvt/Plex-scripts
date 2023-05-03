#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Set the value of the shows setting "auto delete after watching" for all the selected shows
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from typing import List

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

value_mapping = {
	'never': '0',
	'after_day': '1',
	'after_week': '7'
}

def plex_auto_delete(ssn, value: str, library_name: str, series_names: List[str]=[]) -> List[int]:
	result_json = []

	# Setup vars
	value_id = value_mapping.get(value)
	if not value_id:
		return 'Invalid value for "value"'

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory', [])
	for lib in sections:
		if lib['title'] != library_name: continue
		if lib['type'] != 'show': return 'Invalid library'

		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer'].get('Metadata', [])
		for show in lib_output:
			if series_names and not show['title'] in series_names:
				continue

			print(f'	{show["title"]}')
			ssn.put(
				f'{base_url}/library/metadata/{show["ratingKey"]}/prefs',
	   			params={'autoDeletionItemPolicyWatchedLibrary': value_id}
			)
			result_json.append(show['ratingKey'])

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	# Setup arg parsing
	parser = ArgumentParser(description="Set the value of the shows setting \"auto delete after watching\" for all the selected shows")
	parser.add_argument('-v', '--Value', choices=value_mapping.keys(), help="The value that the setting should be set to", required=True)
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target show library", required=True)
	parser.add_argument('-s', '--SeriesName', help="Target a specific series inside a show library based on it's name; This argument can be given multiple times to target multiple series", action='append', default=[])

	args = parser.parse_args()
	# Call function and process result
	response = plex_auto_delete(ssn=ssn, value=args.Value, library_name=args.LibraryName, series_names=args.SeriesName)
	if not isinstance(response, list):
		parser.error(response)
