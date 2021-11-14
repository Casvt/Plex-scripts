#The use case of this script is the following:
#	This script will find any media that has an HDR version but not a SDR version,
#	and will put the media in the optimize-queue to make an optimimzed version that is SDR.
#	Works with movies and show libraries

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests
import re
import getopt
import sys
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

def checkHDR(media_info):
	for media in media_info['Media']:
		for part in media['Part']:
			for stream in part['Stream']:
				if stream['streamType'] == 1 and 'colorSpace' in stream.keys() and re.search('^bt2020', stream['colorSpace']):
					return 'HDR'
	return 'SDR'

def checkOptimize(media_info):
	if media_info['type'] == 'episode' and checkHDR(media_info) == 'SDR': return
	print(str(media_info['title']))
	optimized_found = False
	for media in media_info['Media']:
		if 'title' in media.keys() and re.search('^Optimized for ', media['title']):
			optimized_found = True
			break
	if optimized_found == False:
		print('	Converting')
		plex.fetchItem(media_info['key']).optimize(locationID=-1, targetTagID=2, deviceProfile='Universal TV')

ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
plex = PlexServer('http://' + plex_ip + ':' + plex_port, plex_api_token)

section_output = ssn.get('http://' + plex_ip + ':' + plex_port + '/library/sections').json()
arguments, values = getopt.getopt(sys.argv[1:], 'l:', ['LibraryName='])
lib_ids = []
lib_types = {}
for argument, value in arguments:
	if argument in ('-l', '--LibraryName'):
		lib_found = False
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] in value:
				if level['type'] == 'movie' or level['type'] == 'show':
					lib_found = True
					lib_ids.append(level['key'])
					lib_types[level['key']] = level['type']
				else: print('Warning: library ' + str(value) + ' ignored as it isn\'t a movie or show library')
		if lib_found == False: print('Warning: library ' + str(value) + ' ignored as it isn\'t found')

if not lib_ids:
	print('Error: Arguments were not all given')
	print('Required: -l/--LibraryName [name of target library (movie or show library)')
	print('	Pass this argument multiple times to apply the script to multiple libraries; movie and show libraries are allowed to be mixed')
	exit(1)

for lib in lib_ids:
	if lib_types[lib] == 'movie':
		for movie in ssn.get('http://' + plex_ip + ':' + plex_port + '/library/sections/' + lib + '/all', params={'hdr': '1'}).json()['MediaContainer']['Metadata']:
			checkOptimize(movie)

	elif lib_types[lib] == 'show':
		for show in ssn.get('http://' + plex_ip + ':' + plex_port + '/library/sections/' + lib + '/all', params={'episode.hdr': '1'}).json()['MediaContainer']['Metadata']:
			for episode in ssn.get('http://' + plex_ip + ':' + plex_port + '/library/metadata/' + show['ratingKey'] + '/allLeaves').json()['MediaContainer']['Metadata']:
				episode_output = ssn.get('http://' + plex_ip + ':' + plex_port + '/library/metadata/' + episode['ratingKey']).json()['MediaContainer']['Metadata'][0]
				checkOptimize(episode_output)
