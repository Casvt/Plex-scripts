#The use case of this script is the following:
#	When a stream starts, find the movie script when possible and put it in a file in the movie folder
#
#SETUP:
#In Tautulli, go to Settings -> Notification Agents -> Add a new notification agent -> Script
#	Configuration:
#		Script Folder = folder where this script is stored
#		Script File = select this script
#		Script Timeout = 30
#		Description is optional
#	Triggers:
#		Playback Start = check
#	Conditions:
#		Media Type is movie
#	Arguments:
#		Playback Start -> Script Arguments = --Title {title} --File {file}
#SAVE

import requests
import regex as re
import getopt, sys
import os

arguments, values = getopt.getopt(sys.argv[1:], 't:f:', ['Title=', 'File='])
title = ''
file_path = ''
for argument, value in arguments:
	if argument in ('-t', '--Title'): title = value
	if argument in ('-f', '--File'): file_path = value

if not title or not file_path:
	print('Error: Arguments were not all given')
	print('Required: -t/--Title [title of media], -f/--File [filepath to media file]')
	exit(1)

if not os.path.exists(os.path.dirname(file_path) + '/' + str(title) + '_script.txt'):
	link = re.search('(?i)(Search results for \'' + title + '\'.*?href=\"\K/Movie Scripts/.*?html(?=\" title=\"[^\"]+\">' + title + '))', requests.post('https://imsdb.com/search.php', {'search_query': title, 'submit':'Go%21'}, headers={'X-HTTP-Method-Override': 'GET'}).text).group()
	link = re.search('(?i)(/scripts/.*?\.html)', requests.get('https://imsdb.com' + link).text).group(0)
	script = re.search('<pre>.*</pre>', requests.get('https://imsdb.com' + link).text, re.DOTALL).group().replace('</pre>', '').replace('<pre>', '').replace('</b>', '').replace('<b>', '')
	if script:
		open(os.path.dirname(file_path) + '/' + str(title) + '_script.txt', 'a').write(script)
