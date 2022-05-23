#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Convert a .m3u file to a plex playlist
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from os import path

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def m3u_to_playlist(ssn, library_name: str, file_path: str):
	#check for illegal arg parsing
	if not path.isfile(file_path):
		return 'File not found'

	#loop through the libraries
	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	for lib in sections:
		if lib['title'] == library_name:
			ssn.post(f'{base_url}/playlists/upload', params={'sectionID': lib['key'], 'path': file_path})
			break
	else:
		return 'Library not found'
	return

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Set the first image of an album as the album cover')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library', required=True)
	parser.add_argument('-f','--File', type=str, help="File path to the .m3u file", required=True)

	args = parser.parse_args()
	#call function and process result
	response = m3u_to_playlist(ssn=ssn, library_name=args.LibraryName, file_path=args.File)
	if not response == None:
		parser.error(response)
