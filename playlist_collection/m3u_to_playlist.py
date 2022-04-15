#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Converting an m3u file to a plex playlist
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests, argparse
from os import path

base_url = f'http://{plex_ip}:{plex_port}'
ssn = requests.Session()
ssn.headers.update({'Accept':'application/json'})
ssn.params.update({'X-Plex-Token':plex_api_token})

section_output = ssn.get(f'{base_url}/library/sections').json()
parser = argparse.ArgumentParser(description="Script to convert a .m3u file to a plex playlist")
parser.add_argument('-l','--LibraryName', help="Name of target library", required=True)
parser.add_argument('-f','--File', help="Path to .m3u file", required=True)
args = parser.parse_args()
lib_id = ''
for lib in section_output['MediaContainer']['Directory']:
	if lib['title'] == args.LibraryName:
		lib_id = lib['key']
		break
else:
	parser.error('Library not found')
if not path.exists(args.File):
	parser.error('File not found')

ssn.post(f'{base_url}/playlists/upload', params={'sectionID': lib_id, 'path': args.File})
