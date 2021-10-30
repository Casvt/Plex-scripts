#!/usr/bin/python3

#The use case of this script is the following:
#	Run this script and it will run whatever you want when new media is added to your library
#	That means that if a new movie is added to your movie library, certain code can be executed
#	This is basically the 'recently added' trigger in Tautulli
#	The info about the media is given as a dict inside the variable media_output
#	To see what the structure is of the dict, print it (e.g. print(media_output) ) and see for yourself what kind of information is available

plex_ip = ''
plex_port = ''
plex_api_token = ''

import time
import json
import re
import requests
from plexapi.server import PlexServer

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', plex_ip):
	print("Error: " + plex_ip + " is not a valid ip")
	exit(1)

if not re.search('^\d{1,5}$', plex_port):
	print("Error: " + plex_port + " is not a valid port")
	exit(1)

if not re.search('^[\w\d_-~]{19,21}$', plex_api_token):
	print("Error: " + plex_api_token + " is not a valid api token")
	exit(1)

plex = PlexServer('http://' + plex_ip + ':' + str(plex_port), plex_api_token)

def process(data):
	if data['ActivityNotification'][0]['Activity']['type'] == 'library.update.item.metadata' and data['ActivityNotification'][0]['event'] == 'started':
		media_output = json.loads(requests.get('http://' + plex_ip + ':' + str(plex_port) + str(plex.search(str(re.search('^.*?(?=\()', str(data['ActivityNotification'][0]['Activity']['subtitle'])).group(0)))[0].key), params={'X-Plex-Token': plex_api_token}, headers={'Accept': 'application/json'}).text)
		if int(media_output['MediaContainer']['Metadata'][0]['addedAt']) >= time.time() - 100 and int(media_output['MediaContainer']['Metadata'][0]['addedAt']) <= time.time() + 100:
			print('new media')
			#media item was added to lib
			#This is the place where you want to put your command
			#The command that you put here will be executed when a new item is added to your library
			#You can use media_output (type is dict) to use info about the movie in your command e.g.:
			#	media_output['MediaContainer']['Metadata'][0]['title'] returns title of media
			#	media_output['MediaContainer']['Metadata'][0]['Media'][0]['Part'][0]['file'] returns filepath to media file
			#If you want to run a shell command (like mkvinfo on the media file), you do the following:
			#	import os
			#	os.system('mkvinfo ' + media_output['MediaContainer']['Metadata'][0]['Media'][0]['Part'][0]['file'])

if __name__  == '__main__':
	try:
		listener = plex.startAlertListener(callback=process)
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		listener.stop()
