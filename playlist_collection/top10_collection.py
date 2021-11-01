#!/usr/bin/python3

#The use case of this script is the following:
#	Run this script to add a collection with the 10 most popular movies according to tautulli
#	It is intented to run every so often (use crontab to run it every 12 hours for example)

plex_ip = ''
plex_port = ''
plex_api_token = ''

tautulli_ip = ''
tautulli_port = ''
tautulli_api_token = ''

import re

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', plex_ip):
	print("Error: " + plex_ip + " is not a valid plex ip")
	exit(1)

if not re.search('^\d{1,5}$', plex_port):
	print("Error: " + plex_port + " is not a valid plex port")
	exit(1)

if not re.search('^[\w\d_-~]{19,21}$', plex_api_token):
	print("Error: " + plex_api_token + " is not a valid plex api token")
	exit(1)

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', tautulli_ip):
	print("Error: " + tautulli_ip + " is not a valid tautulli ip")
	exit(1)

if not re.search('^\d{1,5}$', tautulli_port):
	print("Error: " + tautulli_port + " is not a valid tautulli port")
	exit(1)

if not re.search('^[0-9a-z]{32,34}$', tautulli_api_token):
	print("Error: " + tautulli_api_token + " is not a valid tautulli api token")
	exit(1)

import requests
import json
import sys
import getopt

ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
baseurl = 'http://' + plex_ip + ':' + plex_port

section_output = json.loads(ssn.get(baseurl + '/library/sections').text)
rating_keys = []
col_id = ''
arguments, values = getopt.getopt(sys.argv[1:], 'L:', ['LibraryName='])
lib_id = ''
for argument, value in arguments:
	if argument in ('-L', '--LibraryName'):
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == str(value): lib_id = level['key']
		if not lib_id:
			print('Error: library not found')
			exit(1)

if not lib_id:
	print('Error: Required arguments were not all given\n-L/--LibraryName [Name of library to put the collection in]')
	exit(1)

for collection in json.loads(ssn.get(baseurl + '/library/sections/' + lib_id + '/collections').text)['MediaContainer']['Metadata']:
	if collection['title'] == 'Top 10 movies':
		col_id = collection['ratingKey']

if col_id: ssn.delete(baseurl + '/library/collections/' + col_id)
for row in json.loads(requests.get('http://' + tautulli_ip + ':' + tautulli_port + '/api/v2', params={'apikey': tautulli_api_token, 'cmd': 'get_home_stats', 'stat_id': 'top_movies'}).text)['response']['data']['rows']:
	rating_keys.append(str(row['rating_key']))
machine_id = json.loads(ssn.get(baseurl + '/').text)['MediaContainer']['machineIdentifier']
ssn.post(baseurl + '/library/collections', params={'type': 1, 'title': 'Top 10 movies', 'smart': 0, 'sectionId': lib_id, 'uri': 'server://' + machine_id + '/com.plexapp.plugins.library/library/metadata/' + ','.join(rating_keys)})
