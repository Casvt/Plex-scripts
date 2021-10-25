#The use case of this script is the following:
#   The first image in an album will be made the cover of the album.
#   This script applies to every album in every directory (a.k.a every album that exists on your plex server)
#This script requires the following modules: PlexAPI, requests, json, re
#Run this script every once in a while. Every time it is run, the album covers will be updated.
#You can run it every 15 minutes if the cover is important or every 12 hours if you want to keep load low

import requests
import json
import re
from plexapi.server import PlexServer


#ip-address of the plex server
PLEX_IP = ''
#port of the plex server
PLEX_PORT = ''
#api token of the plex server
PLEX_API_TOKEN = ''
#add names of albums to exclude (e.g. if you add 'Album1', albums with the name Album1 will not be processed -> exclusion_name = ['Album1'])
exclusion_name = []
#add names of albums to ONLY process (e.g. if you only want to process albums with the name 'Album2', add it to the list below -> inclusion_name = ['Album2'])
#IF INCLUSION_NAME HAS VALUES, EXCLUSION_NAME WILL BE IGNORED
inclusion_name = []
#add regexes to match against; albums that match regex will be ignored (e.g. exclusion_regex = ['Album\d{1,3}'])
exclusion_regex = []
#add regexes to match against; only albums that match the regex will be processed (e.g. inclusion_regex = ['Album\d{1,3}'])
#IF INCLUSION_REGEX HAS VALUES, EXCLUSION_REGEX WILL BE IGNORED
inclusion_regex = []
#add ratingkeys of albums to exclude from processing (e.g. exclusion_key = ['1666' '123'])
exclusion_key = []
#add ratingkeys of albums to ONLY process (e.g. inclusion_key = ['133' '46'])
#IF INCLUSION_KEY HAS VALUES, EXCLUSION_KEY WILL BE IGNORED
inclusion_key = []

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', PLEX_IP):
	print("Error: " + PLEX_IP + " is not a valid ip")
	exit(1)

if not re.search('^\d{1,5}$', PLEX_PORT):
	print("Error: " + PLEX_PORT + " is not a valid port")
	exit(1)

if not re.search('^[\w\d_-~]{19,21}$', PLEX_API_TOKEN):
	print("Error: " + PLEX_API_TOKEN + " is not a valid api token")
	exit(1)

def reg_loop_ex():
	for regex in exclusion_regex:
		if re.search(regex, album_title): return 1
def reg_loop_in():
	for regex in inclusion_regex:
		if not re.search(regex, album_title): return 1
def recursive_albums(album):
	album_image = ''
	#store the output in a variable and refer to it to reduce web requests
	album_output = json.loads(ssn.get('http://' + PLEX_IP + ':' + PLEX_PORT + album).text)
	#get the title of the album
	album_title = album_output['MediaContainer']['parentTitle']
	#check if the album falls under any of the rules. If the outcome results in the album needing to be denied, execute the return command to skip it
	if reg_loop_ex() == 1: return
	if album_title in exclusion_name: return
	if reg_loop_in() == 1: return
	if inclusion_name and not album_title in inclusion_name: return
	if album_output['MediaContainer']['key'] in exclusion_key: return
	if inclusion_key and not album_output['MediaContainer']['key'] in inclusion_key: return
	#if there are sub-albuns, do them first
	for level in album_output['MediaContainer']['Metadata']:
		if not 'Media' in level.keys():
			#level is an album
			recursive_albums(level['key'])
		elif not album_image: album_image = level
	#if there is a picture present in the album, upload it
	if album_image:
		album_images[album_image['parentRatingKey']] = album_image['Media'][0]['Part'][0]['file']
		plex.fetchItem(int(album_image['parentRatingKey'])).uploadPoster(filepath=str(album_image['Media'][0]['Part'][0]['file']))
	else:
		#there isnt a picture in the album so use the cover of the first sub-album
		for level in album_output['MediaContainer']['Metadata']:
			if not 'Media' in level.keys():
				album_images[level['parentRatingKey']] = album_images[level['ratingKey']]
				plex.fetchItem(int(level['parentRatingKey'])).uploadPoster(filepath=str(album_images[level['ratingKey']]))
				break

album_images = {}
#if the inclusion_name list is populated, empty exclusion_name as it is overridden then
if inclusion_name: exclusion_name = []
#if the inclusion_regex list is populated, empty exclusion_name as it is overridden then
if inclusion_regex: exclusion_regex = []
#if the inclusion_key list is populated, empty exclusion_key as it is overridden then
if inclusion_key: exclusion_key = []
#setup the plex server for Python-PlexAPI
plex = PlexServer('http://' + PLEX_IP + ':' + PLEX_PORT, PLEX_API_TOKEN)

#start a session with standard headers and parameters
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': PLEX_API_TOKEN})

#list all the libraries
resp = json.loads(ssn.get('http://' + PLEX_IP + ':' + PLEX_PORT + '/library/sections').text)['MediaContainer']['Directory']
lib_keys = []
#do this for every library entry
for lib in resp:
	#if the library is a "photo" library, add it to the list
	if lib['type'] == 'photo': lib_keys.append(lib['key'])

#do this for every photo library entry
for key in lib_keys:
	album_keys = []
	#list all albums inside the library and add the keys to the list
	for folders in json.loads(ssn.get('http://' + PLEX_IP + ':' + PLEX_PORT + '/library/sections/' + key + '/all').text)['MediaContainer']['Metadata']: album_keys.append(folders['key'])
	#do this for every album entry
	for album in album_keys:
		recursive_albums(album)
