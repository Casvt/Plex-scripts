#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Apply certain tags to a show (sonarr) or movie (radarr) based on which root folder they are in
	E.g. "if the root folder of the show is '/mnt/plex-media/documentaries', apply the tag 'Docu' to the show"
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly.
	The value of 'sonarr_config' and 'radarr_config' should be following this layout:
		sonarr_config = {
			{{root_folder}}: ['tag1','tag2']
		}
	The key should be the root folder that you want to target and the value should be a list containing the tags that should be applied
	E.g.:
		radarr_config = {
			'/mnt/plex-media/documentaries': ['docu','educational'],
			'/mnt/plex-media/4k-movies': ['4k']
		}
	Apply the tags 'docu' and 'educational' to all movies inside the rootfolder '/mnt/plex-media/documentaries'
	Apply the tag '4k' to all movies inside the rootfolder '/mnt/plex-media/4k-movies'

	Run this script at an interval. Decide for yourself what the interval is (e.g. every 20m or every 12h)
"""

#These need to be filled when you want to use the script with sonarr
sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''
sonarr_config = {}

#These need to be filled when you want to use the script with radarr
radarr_ip = ''
radarr_port = ''
radarr_api_token = ''
radarr_config = {}

from os import getenv
from os.path import dirname
import requests

# Environmental Variables
sonarr_ip = getenv('sonarr_ip', sonarr_ip)
sonarr_port = getenv('sonarr_port', sonarr_port)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
radarr_ip = getenv('radarr_ip', radarr_ip)
radarr_port = getenv('radarr_port', radarr_port)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)
	
def root_folder_tagger(source: str):
	result_json = []

	if source == 'sonarr':
		if sonarr_ip and sonarr_port and sonarr_api_token and sonarr_config:
			#apply script to sonarr
			for setting in sonarr_config.items():
				sonarr_config[setting[0].rstrip('/')] = setting[1]
			sonarr_base_url = f'http://{sonarr_ip}:{sonarr_port}/api/v3'
			sonarr_ssn = requests.Session()
			sonarr_ssn.params.update({'apikey': sonarr_api_token})
			try:
				series_list = sonarr_ssn.get(f'{sonarr_base_url}/series').json()
				tag_list = sonarr_ssn.get(f'{sonarr_base_url}/tag/detail').json()
			except requests.exceptions.ConnectionError:
				print('Error: can\'t connect to sonarr')
				exit(1)

			#loop through all series in sonarr
			for series in series_list:
				series['rootFolderPath'] = series['rootFolderPath'].rstrip('/')
				if series['rootFolderPath'] in sonarr_config.keys():
					target_tags = []
					#note id's of target tags and create tags if they don't exist yet
					for target_tag in sonarr_config[series['rootFolderPath']]:
						for tag in tag_list:
							if tag['label'] == target_tag:
								#target tag already exists
								target_tags.append(tag['id'])
								break
						else:
							#target tag doesn't exist yet
							target_tags.append(sonarr_ssn.post(f'{sonarr_base_url}/tag', json={'label': target_tag}).json()['id'])

					#loop through target tags and add them if they aren't in there yet
					series['tags'] += [t for t in target_tags if not t in series['tags']]
					#upload new tag configuration
					sonarr_ssn.put(f'{sonarr_base_url}/series/{series["id"]}', json=series)
					result_json.append(series["id"])
		else:
			return 'Sonarr set as source but variables not set'

	elif source == 'radarr':
		if radarr_ip and radarr_port and radarr_api_token and radarr_config:
			#apply script to radarr
			for setting in radarr_config.items():
				radarr_config[setting[0].rstrip('/')] = setting[1]
			radarr_base_url = f'http://{radarr_ip}:{radarr_port}/api/v3'
			radarr_ssn = requests.Session()
			radarr_ssn.params.update({'apikey': radarr_api_token})
			try:
				movie_list = radarr_ssn.get(f'{radarr_base_url}/movie').json()
				tag_list = radarr_ssn.get(f'{radarr_base_url}/tag').json()
			except requests.exceptions.ConnectionError:
				print('Error: can\'t connect to radarr')
				exit(1)

			#loop through all movies in radarr
			for movie in movie_list:
				movie['rootFolderPath'] = dirname(movie['path'])
				if movie['rootFolderPath'] in radarr_config.keys():
					target_tags = []
					#note id's of target tags and create tags if they don't exist yet
					for target_tag in radarr_config[movie['rootFolderPath']]:
						for tag in tag_list:
							if tag['label'] == target_tag:
								#target tag already exists
								target_tags.append(tag['id'])
								break
						else:
							#target tag doesn't exist yet
							target_tags.append(radarr_ssn.post(f'{radarr_base_url}/tag', json={'label': target_tag}).json()['id'])

					#loop through target tags and add them if they aren't in there yet
					movie['tags'] += [t for t in target_tags if not t in movie['tags']]
					#upload new tag configuration
					movie.pop('rootFolderPath')
					radarr_ssn.put(f'{radarr_base_url}/movie/{movie["id"]}', json=movie)
					result_json.append(movie["id"])
		else:
			return 'Radarr set as source but variables not set'

	return result_json

if __name__ == '__main__':
	import argparse

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Apply certain tags to a show (sonarr) or movie (radarr) based on which root folder they are in")
	parser.add_argument('-s', '--Source', type=str, choices=['sonarr','radarr'], help="Select the source which media should be checked", required=True)

	args = parser.parse_args()
	#call function and process result
	response = root_folder_tagger(source=args.Source)
	if not isinstance(response, list):
		parser.error(response)