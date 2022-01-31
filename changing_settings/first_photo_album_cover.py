#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	The first image in an album will be made the cover of the album.
	This script applies to every album in every directory (a.k.a every album that exists on your plex server)
Requirements (python3 -m pip install [requirement]):
	requests, PlexAPI
Setup:
	Fill the variables below firstly, then run the script.
	Run this script every once in a while. Every time it is run, the album covers will be updated.
	You can run it every 15 minutes if the cover is important or every 12 hours if you want to keep load low
"""

import requests
import re

plex_ip = ''
plex_port = ''
plex_api_token = ''
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

def reg_loop_ex():
	for regex in exclusion_regex:
		if re.search(regex, album_title): return 1

def reg_loop_in():
	for regex in inclusion_regex:
		if not re.search(regex, album_title): return 1

def recursive_albums(album):
	album_image = ''
	album_output = ssn.get('http://' + plex_ip + ':' + plex_port + album).json()
	album_title = album_output['MediaContainer']['parentTitle']
	#check if the album falls under any of the rules
	if reg_loop_ex() == 1: return
	if album_title in exclusion_name: return
	if reg_loop_in() == 1: return
	if inclusion_name and not album_title in inclusion_name: return
	if album_output['MediaContainer']['key'] in exclusion_key: return
	if inclusion_key and not album_output['MediaContainer']['key'] in inclusion_key: return
	#if there are sub-albuns, do them first
	for level in album_output['MediaContainer']['Metadata']:
		if not 'Media' in level.keys():
			recursive_albums(level['key'])
		elif not album_image: album_image = level
	#if there is a picture present in the album, upload it
	if album_image:
		album_images[album_image['parentRatingKey']] = album_image['Media'][0]['Part'][0]['file']
		requests.post(f'http://{plex_ip}:{plex_port}/library/metadata/{album_image["parentRatingKey"]}/posters', data=open(album_image['Media'][0]['Part'][0]['file'], 'rb').read())
	else:
		#there isnt a picture in the album so use the cover of the first sub-album
		for level in album_output['MediaContainer']['Metadata']:
			if not 'Media' in level.keys():
				album_images[level['parentRatingKey']] = album_images[level['ratingKey']]
				requests.post(f'http://{plex_ip}:{plex_port}/library/metadata/{level["parentRatingKey"]}/posters', data=open(album_images[level['ratingKey']], 'rb').read())
				break

album_images = {}
if inclusion_name: exclusion_name = []
if inclusion_regex: exclusion_regex = []
if inclusion_key: exclusion_key = []

ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
base_url = 'http://' + plex_ip + ':' + plex_port

resp = ssn.get(base_url + '/library/sections').json()['MediaContainer']['Directory']
lib_keys = [lib['key'] for lib in resp if lib['type'] == 'photo']

for key in lib_keys:
	album_keys = [folders['key'] for folders in ssn.get(base_url + '/library/sections/' + key + '/all').json()['MediaContainer']['Metadata']]
	for album in album_keys:
		recursive_albums(album)
