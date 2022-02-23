#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Automatically skip intro's and advertisements of the media (plex pass needed for plex to automatically mark intro's and advertisements in media files)
	Intro's and advertisements can be marked by markers or by chapters
Requirements (python3 -m pip install [requirement]):
	PlexAPI
	websocket-client
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Once this script is run, it will keep running and will handle streams accordingly when needed.
	Run it in the background as a service or as a '@reboot' cronjob (cron only available on unix systems (linux and mac)).
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import time, requests, logging, argparse
from plexapi.server import PlexServer

base_url = f'http://{plex_ip}:{plex_port}'
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
plex = PlexServer(base_url, plex_api_token)

logging_level = logging.INFO
logging.basicConfig(level=logging_level, format='[%(asctime)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S %d-%m-20%y')

parser = argparse.ArgumentParser(
	description="Skip intro's and advertisements in media",
	epilog=f"example:\n  {__file__} -i -a\n	Skip intro's and advertisements",
	formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-i','--Intro', help="Enable the script to skip intro's", action='store_true')
parser.add_argument('-o','--Outro', help="Enable the script to skip outro's", action='store_true')
parser.add_argument('-a','--Advertisements', help="Enable the script to skip advertisements", action='store_true')
args = parser.parse_args()

media_output = {}

def move(player, time):
	#move stream to end of chapter/marker
	minutes = time / 1000 / 60
	seconds = int(minutes % 1 * 60)
	minutes = int(minutes)
	logging.info(f'Moving stream playing on {player} to {minutes}:{seconds}')
	try:
		plex.client(player).seekTo(time, mtype='video')
		logging.info('Success')
	except Exception as e:
		logging.exception('Failed: ')
	return

def chapter_check(data, rating_key, player):
	#check if stream is currently in chapter that needs to be skipped
	if 'Chapter' in media_output[rating_key].keys():
		for chapter in media_output[rating_key]['Chapter']:
			if not 'tag' in chapter.keys(): continue
			if (args.Intro == True and chapter['tag'].lower() == 'intro') or (args.Outro == True and chapter['tag'].lower() == 'outro') or (args.Advertisements == True and chapter['tag'].lower() in ('ad','ads','advertisement','advertisements')):
				if chapter['startTimeOffset'] <= data['viewOffset'] <= chapter['endTimeOffset']:
					#current chapter needs to be skipped
					move(player, chapter['endTimeOffset'])
					return 'Moved'
	return 'Not-Moved'

def marker_check(data, rating_key, player):
	#check if stream is currently in marker that needs to be skipped
	if 'Marker' in media_output[rating_key].keys():
		for marker in media_output[rating_key]['Marker']:
			if not 'type' in marker.keys(): continue
			if (args.Intro == True and marker['type'].lower() == 'intro') or (args.Outro == True and marker['type'].lower() == 'outro') or (args.Advertisements == True and marker['type'].lower() in ('ad','ads','advertisement','advertisements')):
				if marker['startTimeOffset'] <= data['viewOffset'] <= marker['endTimeOffset']:
					#current marked area needs to be skipped
					move(player, marker['endTimeOffset'])
					return 'Moved'
	return 'Not-Moved'

def process(data):
	if data['type'] == 'playing':
		logging.debug(data)
		data = data['PlaySessionStateNotification'][0]
		rating_key = str(data['ratingKey'])
		for session in ssn.get(f'{base_url}/status/sessions').json()['MediaContainer']['Metadata']:
			logging.debug(session)
			if str(session['sessionKey']) == str(data['sessionKey']):
				#session found
				if not session['Session']['location'] == 'lan': return
				media_output[rating_key] = ssn.get(f'{base_url}/library/metadata/{rating_key}', params={'includeChapters': 1, 'includeMarkers': 1}).json()['MediaContainer']['Metadata'][0]
				logging.debug(media_output[rating_key])
				#check for chapters and skip if needed
				if chapter_check(data, rating_key, session['Player']['title']) == 'Moved': return
				marker_check(data, rating_key, session['Player']['title'])
				return
		else:
			logging.error('Not able to find session back in status')
			return

if __name__  == '__main__':
	if args.Intro == False and args.Outro == False and args.Advertisements == False:
		parser.print_help()
		parser.error('At least one of three actions must be selected')
	logging.info('Handling streams...')
	if args.Intro == True: logging.info('Skipping intro\'s when needed')
	if args.Outro == True: logging.info('Skipping outro\'s when needed')
	if args.Advertisements == True: logging.info('Skipping advertisements when needed')
	try:
		listener = plex.startAlertListener(callback=process)
		while True: time.sleep(1)
	except KeyboardInterrupt:
		logging.info('Shutting down')
		listener.stop()
