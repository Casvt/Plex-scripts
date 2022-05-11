#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	When a stream starts, find the movie script when possible and put it in a file in the movie folder
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Go to the tautulli web-ui -> Settings -> Notification Agents -> Add a new notification agent -> Script:
		Configuration:
			Script Folder = /path/to/script/folder
			Script File = select this script
			Script Timeout = 30
			Description = whatever you want
		Triggers:
			Playback Start = check
		Conditions:
			Media Type is movie
		Arguments:
			Playback Start -> Script Arguments = --Title {title} --File {file}
"""

import os, requests, re

def _find_script(title):
	#search for movie
	output = requests.post('https://imsdb.com/search.php', params={'search_query': title, 'submit':'Go%21'}, headers={'X-HTTP-Method-Override': 'GET'}).text
	web_link = re.findall('(?i)(?:(?<=href=")/Movie Scripts/.*?\.html(?=" title="[^"]+">' + title + '))', output)
	if not web_link:
		#movie not found in search
		return None
	else:
		#movie found in search; selected first result
		web_link = web_link[0]

	#search for movie script
	output = requests.get('https://imsdb.com' + web_link).text
	script_link = re.findall('(?i)(/scripts/.*?\.html)', output)
	if not script_link:
		#movie found but no script attached
		return None
	else:
		#movie found and also link to script
		script_link = script_link[0]

	#get script and clean up
	output = requests.get('https://imsdb.com' + script_link).text
	script = re.findall('<pre>.+</pre>', output, re.DOTALL)
	if not script:
		#movie found but no script content
		return None
	else:
		#movie found and also complete script
		script = script[0].replace('</pre>', '').replace('<pre>', '').replace('</b>', '').replace('<b>', '')

	return script

def moviescript_sender(movie_title: str, movie_file: str):
	result_json = []

	#check for illegal arg parsing
	if not os.path.isfile(movie_file):
		return 'Media file not found'

	#check if script doesn't already exist
	file_path = os.path.splitext(movie_file)[0] + '_script.txt'
	result_json.append(file_path)
	if not os.path.isfile(file_path):
		#script doesn't already exist
		script = _find_script(movie_title)
		if script != None:
			#script found
			with open(file_path, 'w') as f:
				f.write(script)

	return result_json

if __name__ == '__main__':
	import argparse

	#setup arg parsing
	parser = argparse.ArgumentParser(description="When a stream starts, find the movie script when possible and put it in a file in the movie folder")
	parser.add_argument('-t','--Title', help="Title of the media", required=True)
	parser.add_argument('-f','--File', help="Filepath to media file", required=True)

	args = parser.parse_args()
	#call function and process result
	response = moviescript_sender(args.Title, args.File)
	print(response)
