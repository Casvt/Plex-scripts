#!/usr/bin/python3
#-*- encoding: utf-8 -*-

"""
The use case of this script is the following:
	After watching a movie, move the movie file from one folder to another.
IMPORTANT:
	The thing that will be moved is the movie file but the sub-folder that its in will also be copied
	EXAMPLE:
		/mnt/plex-media/movies/cars/cars.mkv (movie file) + /mnt/plex-media/movies (source folder)
		->
		/mnt/plex-media-2/movies/cars/cars.mkv (/mnt/plex-media-2/movies = target folder)

		/mnt/plex-media/movies/cars.mkv (movie file) + /mnt/plex-media/movies (source folder)
                ->
                /mnt/plex-media-2/movies/cars.mkv (/mnt/plex-media-2/movies = target folder)

Requirements (pip3 install ...):
	requests, PlexAPI

To-Do:
	1. Better argument parsing.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests
import sys, getopt
import time
import os, shutil
from plexapi.server import PlexServer

arguments, values = getopt.getopt(sys.argv[1:], 'S:T:', ['S=', 'T='])
source_folder = ''
target_folder = ''
for argument, value in arguments:
	if argument in ('-S', '--SourceFolder'):
		if os.path.isdir(value):
			source_folder = value
		else:
			print('Error: source folder not found')
			exit(1)
	if argument in ('-T', '--TargetFolder'):
		if os.path.isdir(value):
			target_folder = value
		else:
			print('Error: target folder not found')
			exit(1)

if not (source_folder and target_folder):
	print('Error: Arguments were not all given')
	print('Required:\n	-S/--SourceFolder [folder path]\n		If a movie whose file is in this folder or sub-folder of this folder, move it when watched')
	print('	-T/--TargetFolder [folder path]\n		Move file/folder to here')
	print('\nOnly the file is moved though any sub-folders that the file is in in the source folder are re-made in the target folder to keep folder structure.')
	exit(1)

baseurl = 'http://' + plex_ip + ':' + str(plex_port)
plex = PlexServer(baseurl, plex_api_token)
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})

def process(data):
	if data['PlaySessionStateNotification'][0]['state'] == 'stopped':
		media_output = ssn.get(baseurl + '/library/metadata/' + str(data['PlaySessionStateNotification'][0]['ratingKey'])).json()
		if media_output['MediaContainer']['Metadata'][0]['type'] == 'movie':
			for media in media_output['MediaContainer']['Metadata'][0]['Media']:
				for part in media['Part']:
					dest = os.path.join(target_folder, part['file'].lstrip(source_folder))
					if str(dest) == str(part['file']): continue
					os.makedirs(os.path.dirname(dest), exist_ok=True)
					shutil.move(part['file'], dest)
					print(part['file'] + ' moved to ' + dest)

if __name__  == '__main__':
	try:
		print('Watched movies will now be handled!')
		listener = plex.startAlertListener(callback=process)
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		listener.stop()
