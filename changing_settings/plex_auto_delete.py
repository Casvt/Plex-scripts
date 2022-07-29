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

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def plex_auto_delete(ssn, value: str, library_name: str, series_name: list=[]):
	result_json = []

	#check for illegal arg parsing
	if not value in ('never','after_day','after_week'):
		return 'Invalid value for "value"'

	#setup vars
	if value == 'never': value_id = '0'
	elif value == 'after_day': value_id = '1'
	elif value == 'after_week': value_id = '7'

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] != library_name: continue
		if lib['type'] != 'show': return 'Invalid library'

		#this library is targeted
		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer']['Metadata']
		#loop through the shows in the library
		for show in lib_output:
			if series_name and not show['title'] in series_name:
				#a specific show is targeted and this one is not it, so skip
				continue

			print(f'	{show["title"]}')
			#set value of setting
			ssn.put(f'{base_url}/library/metadata/{show["ratingKey"]}/prefs', params={'autoDeletionItemPolicyWatchedLibrary': value_id})
			result_json.append(show['ratingKey'])

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Set the value of the shows setting \"auto delete after watching\" for all the selected shows")
	parser.add_argument('-v', '--Value', choices=['never','after_day','after_week'], help="The value that the setting should be set to", required=True)
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target show library", required=True)
	parser.add_argument('-s', '--SeriesName', help="Target a specific series inside a show library based on it's name; This argument can be given multiple times to target multiple series", action='append', default=[])

	args = parser.parse_args()
	#call function and process result
	response = plex_auto_delete(ssn=ssn, value=args.Value, library_name=args.LibraryName, series_name=args.SeriesName)
	if not isinstance(response, list):
		parser.error(response)
