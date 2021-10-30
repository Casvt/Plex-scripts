#!/usr/bin/python3

#The use case of this script is the following:
#	Automatically skip intro's and advertisements of the media (plex pass needed for plex to mark intro's and advertisements in media files)

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
media_output = {}
media_chapters = {}
media_markers = {}
media_session = {}

def move(data):
	#media is inside chapter marked as advertisement or intro; check if media is played locally as we can only control stream on lan
	if not data['PlaySessionStateNotification'][0]['ratingKey'] in media_session.keys():
		for session in json.loads(requests.get('http://' + plex_ip + ':' + plex_port + '/status/sessions', params={'X-Plex-Token': plex_api_token}, headers={'Accept': 'application/json'}).text)['MediaContainer']['Metadata']:
			if session['sessionKey'] == str(data['PlaySessionStateNotification'][0]['sessionKey']): media_session[data['PlaySessionStateNotification'][0]['ratingKey']] = session
	if media_session[data['PlaySessionStateNotification'][0]['ratingKey']]['Session']['location'] == 'lan':
		#media is played on lan; move stream to end of chapter
		plex.client(media_session[data['PlaySessionStateNotification'][0]['ratingKey']]['Player']['title'], identifier=data['PlaySessionStateNotification'][0]['clientIdentifier']).seekTo(level['endTimeOffset'], mtype='video')

def process(data):
	print(json.dumps(data, indent=4))
	if data['type'] == 'playing':
		if data['PlaySessionStateNotification'][0]['ratingKey'] in media_session.keys() and not media_session[data['PlaySessionStateNotification'][0]['ratingKey']]['Session']['location'] == 'lan': return
		if not data['PlaySessionStateNotification'][0]['ratingKey'] in media_output.keys(): media_output[data['PlaySessionStateNotification'][0]['ratingKey']] = json.loads(requests.get('http://' + plex_ip + ':' + str(plex_port) + data['PlaySessionStateNotification'][0]['key'], params={'X-Plex-Token': plex_api_token}, headers={'Accept': 'application/json'}).text)
		if not data['PlaySessionStateNotification'][0]['ratingKey'] in media_chapters.keys() and 'Chapter' in media_output[data['PlaySessionStateNotification'][0]['ratingKey']]['MediaContainer']['Metadata'][0].keys(): media_chapters[data['PlaySessionStateNotification'][0]['ratingKey']] = media_output[data['PlaySessionStateNotification'][0]['ratingKey']]['MediaContainer']['Metadata'][0]['Chapter']
		if not data['PlaySessionStateNotification'][0]['ratingKey'] in media_markers.keys() and 'Marker' in media_output[data['PlaySessionStateNotification'][0]['ratingKey']]['MediaContainer']['Metadata'][0].keys(): media_markers[data['PlaySessionStateNotification'][0]['ratingKey']] = media_output[data['PlaySessionStateNotification'][0]['ratingKey']]['MediaContainer']['Metadata'][0]['Marker']
		for level in media_chapters[data['PlaySessionStateNotification'][0]['ratingKey']]:
			if data['PlaySessionStateNotification'][0]['viewOffset'] >= level['startTimeOffset'] and data['PlaySessionStateNotification'][0]['viewOffset'] < level['endTimeOffset'] and 'tag' in level.keys() and level['tag'] == 'Advertisement':
				move(data)
				break
		for level in media_markers[data['PlaySessionStateNotification'][0]['ratingKey']]:
			if data['PlaySessionStateNotification'][0]['viewOffset'] >= level['startTimeOffset'] and data['PlaySessionStateNotification'][0]['viewOffset'] < level['endTimeOffset'] and 'type' in level.keys() and level['type'] == 'intro':
				move(data)
				break

if __name__  == '__main__':
	try:
		listener = plex.startAlertListener(callback=process)
		while True: time.sleep(1)
	except KeyboardInterrupt: listener.stop()
