#!/usr/bin/python3
#The use case of this script is the following:
#	If the media has not been watched for x days, falls outside of the x newest episodes, has been watched for x or more times or has been added x or more days ago,
#	act on the media by, for example, deleting the file and removing it from your library

plex_ip = ''
plex_port = ''
plex_api_token = ''

import re

if not re.search('^(\d{1,3}\.){3}\d{1,3}$', plex_ip):
	print("Error: " + plex_ip + " is not a valid ip")
	exit(1)

if not re.search('^\d{1,5}$', plex_port):
	print("Error: " + plex_port + " is not a valid port")
	exit(1)

if not re.search('^[\w\d_-~]{19,21}$', plex_api_token):
	print("Error: " + plex_api_token + " is not a valid api token")
	exit(1)

import requests
import json
import getopt
import sys
import time

#This function will be run for every episode that falls under the conditions (e.g. to be removed).
#You can change this function to do anything you want with the episode.
#The dict 'episode_object' contains information about the episode that you can use.
def action(episode_object):
#don't comment out the True unless you add an action below
	True
#show content of episode_object
#	print(episode_object)
#remove the media (a.k.a. removing the file(s))
#	ssn.delete(baseurl + '/library/metadata/' + episode_object['ratingKey'])

def episode(episode_object):
	if 	(days_old and 'lastViewedAt' in episode_object.keys() and int(episode_object['lastViewedAt']) < int(time.time()) - (days_old * 86400)) or \
		(days_added and int(episode_object['addedAt']) < int(time.time()) - (days_added * 86400)) or \
		(view_count and 'viewCount' in episode_object.keys() and int(episode_object['viewCount']) >= view_count): #86400 = 1 day in epoch/seconds
		print(episode_object['grandparentTitle'] + ' - S' + str(episode_object['parentIndex']) + 'E' + str(episode_object['index']) + ' - ' + episode_object['title'])
		action(episode_object)
		return
	if recent_episodes:
		if not episode_object['grandparentRatingKey'] in latest_episodes.keys():
			latest_episodes[episode_object['grandparentRatingKey']] = []
			for episode in json.loads(ssn.get(baseurl + '/library/metadata/' + episode_object['grandparentRatingKey'] + '/allLeaves').text)['MediaContainer']['Metadata'][recent_episodes:]:
				latest_episodes[episode_object['grandparentRatingKey']].append(episode['ratingKey'])
		if not episode_object['ratingKey'] in latest_episodes[episode_object['grandparentRatingKey']]:
			print(episode_object['grandparentTitle'] + ' - S' + str(episode_object['parentIndex']) + 'E' + str(episode_object['index']) + ' - ' + episode_object['title'])
			action(episode_object)
			return

ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
baseurl = 'http://' + plex_ip + ':' + plex_port

section_output = json.loads(ssn.get(baseurl + '/library/sections').text)
arguments, values = getopt.getopt(sys.argv[1:], 'hD:R:V:A:L:S:s:e:', ['Help', 'DaysOld=', 'RecentEpisodes=', 'ViewCount=', 'DaysAdded=', 'LibraryName=', 'Series=', 'SeasonNumber=', 'EpisodeNumber='])
days_old = ''
recent_episodes = ''
view_count = ''
days_added = ''
lib_id = ''
series_id = ''
season_id = ''
episode_id = ''
latest_episodes = {}
for argument, value in arguments:
	if argument in ('-h', '--Help'):
		print('The arguments to use this script:\nIMPORTANT: The arguments need to be given in the order that they are shown here!')
		print('Required (the \'AND/OR\' arguments are evaluated as \'or\' (so the media will be removed if it matches -D OR -R OR -V OR -A)):\n	-D/--DaysOld [how many days ago the media was watched for the last time]\n	AND/OR\n	-R/--RecentEpisodes [the number of recent episodes to keep (e.g. only keep the newest x episodes)]\n	AND/OR\n	-V/--ViewCount [remove if media has x or more views]\n	AND/OR\n	-A/--DaysAdded [remove if media has been added x or more days ago]\n\n	-L/--LibraryName [name of target library]')
		print('Optional:\n	-S/--Series [target series name]\n	-s/--SeasonNumber [number of the target season]\n	-e/--EpisodeNumber [number of the target episode]')
		print('When --Series is given, the whole series is processed; when --SeasonNumber is given, the whole season of the series is processed; when --EpisodeNumber is given, that specific episode of that specific season is processed')
		exit()
	if argument in ('-D', '--DaysOld'):
		if re.search('^\d+$', value): days_old = int(value)
		else:
			print('Error: days-old given is not a number')
			exit(1)

	if argument in ('-R', '--RecentEpisodes'):
		if re.search('^\d+$', value): recent_episodes = int(value) * -1
		else:
			print('Error: recent-episodes given is not a number')
			exit(1)

	if argument in ('-V', '--ViewCount'):
		if re.search('^\d+$', value): view_count = int(value)
		else:
			print('Error: view-count given is not a number')
			exit(1)

	if argument in ('-A', '--DaysAdded'):
		if re.search('^\d+$', value): days_added = int(value)
		else:
			print('Error: days-added given is not a number')
			exit(1)

	if argument in ('-L', '--LibraryName'):
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] == str(value) and level['type'] == 'show': lib_id = level['key']
		if not lib_id:
			print('Error: library not found or not a show library')
			exit(1)

	if argument in ('-S', '--Series'):
		for level in json.loads(ssn.get(baseurl + '/library/sections/' + lib_id + '/all').text)['MediaContainer']['Metadata']:
			if level['title'] == str(value): series_id = level['ratingKey']
		if not series_id:
			print('Error: series not found or arguments not given in correct order')
			exit(1)

	if argument in ('-s', '--SeasonNumber'):
		for level in json.loads(ssn.get(baseurl + '/library/metadata/' + series_id + '/children').text)['MediaContainer']['Metadata']:
			if level['index'] == int(value): season_id = level['ratingKey']
		if not season_id:
			print('Error: season not found or arguments not given in correct order')
			exit(1)

	if argument in ('-e', '--EpisodeNumber'):
		for level in json.loads(ssn.get(baseurl + '/library/metadata/' + season_id + '/children').text)['MediaContainer']['Metadata']:
			if level['index'] == int(value): episode_id = level
		if not episode_id:
			print('Error: episode not found or arguments not given in correct order')
			exit(1)

if not lib_id or not (days_old or recent_episodes or view_count or days_added):
	print('Error: Required arguments were not all given\nrun recent_episode_maintainer.py -h')
	exit(1)

if episode_id:
	#change an episode
	episode(episode_id)
elif season_id:
	#change a season
	for episodes in json.loads(ssn.get(baseurl + '/library/metadata/' + season_id + '/children').text)['MediaContainer']['Metadata']:
		episode(episodes)
elif series_id:
	#change a series
	for season in json.loads(ssn.get(baseurl + '/library/metadata/' + series_id + '/children').text)['MediaContainer']['Metadata']:
		for episodes in json.loads(ssn.get(baseurl + '/library/metadata/' + season['ratingKey'] + '/children').text)['MediaContainer']['Metadata']:
			episode(episodes)
elif lib_id:
	#change a library
	for series in json.loads(ssn.get(baseurl + '/library/sections/' + lib_id + '/all').text)['MediaContainer']['Metadata']:
		for season in json.loads(ssn.get(baseurl + '/library/metadata/' + series['ratingKey'] + '/children').text)['MediaContainer']['Metadata']:
			for episodes in json.loads(ssn.get(baseurl + '/library/metadata/' + season['ratingKey'] + '/children').text)['MediaContainer']['Metadata']:
				episode(episodes)
