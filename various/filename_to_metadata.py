#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Get the plex metadata for a file
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from os.path import isfile

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def filename_to_metadata(ssn, filepath: str):
	if not isfile(filepath):
		return 'File not found'

	#find library that file is in
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	for lib in sections:
		for loc in lib['Location']:
			if loc['path'] in filepath:
				lib_id = lib['key']
				content_type = '1' if lib['type'] == 'movie' else '4'
				break
		else:
			continue
		break
	else:
		return 'File not found in any plex library'

	#find file in library
	lib_output = ssn.get(f'{base_url}/library/sections/{lib_id}/all', params={'type': content_type}).json()['MediaContainer']['Metadata']
	for entry in lib_output:
		for media in entry['Media']:
			for part in media['Part']:
				if part['file'] == filepath:
					return entry
	return 'Media not found in plex library'

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Get the plex metadata for a file')
	parser.add_argument('-f','--Filepath', type=str, help='The file path to the file', required=True)

	args = parser.parse_args()
	#call function and process result
	response = filename_to_metadata(ssn=ssn, filepath=args.Filepath)
	if isinstance(response, dict):
		from json import dumps
		print(dumps(response, indent=4))
	else:
		parser.error(response)

