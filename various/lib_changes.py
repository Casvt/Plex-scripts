#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Run this script and it will run whatever you want when new media is added to your library
	That means that if a new movie is added to your movie library, certain code can be executed
	This is basically the 'recently added' trigger in Tautulli
	The info about the media is given as a dict inside the variable media_output
	To see what the structure is of the dict, print it (e.g. print(media_output) ) and see for yourself what kind of information is available
Requirements (python3 -m pip install [requirement]):
	PlexAPI
	websocket-client
	requests
Setup:
	Fill the variables below firstly, and add the commands you want to run on line 49->
	Once this script is run, it will keep running and will handle new media accordingly when needed.
	Run it in the background as a service or as a '@reboot' cronjob (cron only available on unix systems (linux and mac)).
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import time, re, requests, logging
from plexapi.server import PlexServer

base_url = f'http://{plex_ip}:{plex_port}'
plex = PlexServer(base_url, plex_api_token)
logging_level = logging.INFO
logging.basicConfig(level=logging_level, format='[%(asctime)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S %d-%m-20%y')

def process(data):
	if not 'ActivityNotification' in data.keys(): return
	data = data['ActivityNotification'][0]
	logging.debug(data)
	if data['Activity']['type'] == 'library.update.item.metadata' and data['event'] == 'started':
		media_key = plex.search(str(re.search("^.*?(?=\()", str(data['Activity']['subtitle'])).group(0)))[0].key
		media_output = requests.get(f'{base_url}{media_key}', params={'X-Plex-Token': plex_api_token}, headers={'Accept': 'application/json'}).json()
		logging.debug(media_output)
		if time.time() + 100 >= int(media_output['MediaContainer']['Metadata'][0]['addedAt']) >= time.time() - 100:
			logging.info('New Media')
			#media item was added to lib
			#This is the place where you want to put your command(s)
			#The command(s) that you put here will be executed when a new item is added to your library
			#You can use media_output (type is dict) to use info about the media in your command(s) e.g.:
			#	media_output['MediaContainer']['Metadata'][0]['title'] returns title of media
			#	media_output['MediaContainer']['Metadata'][0]['Media'][0]['Part'][0]['file'] returns filepath to media file
			#If you want to run a shell command (like mkvinfo on the media file), you do the following:
			#	import os
			#	os.system('mkvinfo ' + media_output['MediaContainer']['Metadata'][0]['Media'][0]['Part'][0]['file'])

if __name__  == '__main__':
	logging.info('Handling new media...')
	try:
		listener = plex.startAlertListener(callback=process)
		while True: time.sleep(5)
	except KeyboardInterrupt:
		logging.info('Shutting down')
		listener.stop()
