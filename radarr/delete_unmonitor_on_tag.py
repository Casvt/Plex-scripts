#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Delete the movie file and unmonitor the movie in radarr if it has a certain tag
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

radarr_ip = ''
radarr_port = ''
radarr_api_token = ''

from os import getenv

# Environmental Variables
radarr_ip = getenv('radarr_ip', radarr_ip)
radarr_port = getenv('radarr_port', radarr_port)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)
base_url = f"http://{radarr_ip}:{radarr_port}/api/v3"

def delete_unmonitor_on_tag(ssn, tag_name: str, delete_file: bool, unmonitor_movie: bool):
	result_json = []

	#check for illegal arg parsing
	if not any((delete_file, unmonitor_movie)):
		return 'Either "delete_file", "unmonitor_movie" or both have to be selected'

	#get id of tag
	tags = ssn.get(f'{base_url}/tag').json()
	for tag in tags:
		if tag['label'] == tag_name:
			tag_id = tag['id']
			break
	else:
		return 'Tag not found'

	#process movies with the tag applied
	movies = ssn.get(f'{base_url}/movie').json()
	for movie in movies:
		if tag_id in movie['tags']:
			#movie found with tag applied; process
			print(movie['title'])
			if delete_file == True and 'movieFile' in movie:
				ssn.delete(f'{base_url}/movieFile/{movie["movieFile"]["id"]}')

			if unmonitor_movie == True:
				movie['monitored'] = False
				ssn.put(f'{base_url}/movie/{movie["id"]}', json=movie)

			result_json.append(movie['id'])

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.params.update({'apikey': radarr_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Delete the movie file and unmonitor the movie in radarr if it has a certain tag')
	parser.add_argument('-t','--TargetTag', type=str, help='Name of target tag', required=True)
	parser.add_argument('-d','--DeleteFile', help='Enable deleting the movie file', action='store_true')
	parser.add_argument('-u','--UnmonitorMovie', help='Enable unmonitoring the movie', action='store_true')

	args = parser.parse_args()
	#call function and process result
	response = delete_unmonitor_on_tag(ssn=ssn, tag_name=args.TargetTag, delete_file=args.DeleteFile, unmonitor_movie=args.UnmonitorMovie)
	if not isinstance(response, list):
		if response == 'Either "delete_file", "unmonitor_movie" or both have to be selected':
			parser.error('Either -d/--DeleteFile, -u/--UnmonitorMovie or both have to be selected')
		else:
			parser.error(response)
