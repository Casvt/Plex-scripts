#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Delete media files in sonarr/radarr that have the codec given and initiate a new search for them
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

#These need to be filled when you want to use the script with sonarr
sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''

#These need to be filled when you want to use the script with radarr
radarr_ip = ''
radarr_port = ''
radarr_api_token = ''

from os import getenv
import requests

# Environmental Variables
sonarr_ip = getenv('sonarr_ip', sonarr_ip)
sonarr_port = getenv('sonarr_port', sonarr_port)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
radarr_ip = getenv('radarr_ip', radarr_ip)
radarr_port = getenv('radarr_port', radarr_port)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)

def remove_codec(source: str, codec: str):
	result_json = []

	if source == 'sonarr':
		if sonarr_ip and sonarr_port and sonarr_api_token:
			#apply script to sonarr
			sonarr_base_url = f'http://{sonarr_ip}:{sonarr_port}/api/v3'
			sonarr_ssn = requests.Session()
			sonarr_ssn.params.update({'apikey': sonarr_api_token})
			try:
				series_list = sonarr_ssn.get(f'{sonarr_base_url}/series').json()
			except requests.exceptions.ConnectionError:
				return 'Can\'t connect to Sonarr'

			#loop through all series in sonarr
			for series in series_list:
				episode_list = sonarr_ssn.get(f'{sonarr_base_url}/episode', params={'seriesId': series['id']}).json()
				for episode in episode_list:
					episode_output = sonarr_ssn.get(f'{sonarr_base_url}/episodeFile/{episode["episodeFileId"]}').json()
					if episode_output['mediaInfo']['videoCodec'] == codec:
						#episode matches codec; replace it
						print(episode_output['path'])
						#delete media file
						sonarr_ssn.delete(f'{sonarr_base_url}/episodeFile/{episode_output["id"]}', params={'episodeEntity': 'episodes'})
						#start search for new file
						sonarr_ssn.post(f'{sonarr_base_url}/command', json={'name':'EpisodeSearch', 'episodeIds': [episode['id']]})
						result_json.append(episode['id'])
		else:
			return 'Sonarr set as source but variables not set'

	elif source == 'radarr':
		if radarr_ip and radarr_port and radarr_api_token:
			#apply script to sonarr
			radarr_base_url = f'http://{radarr_ip}:{radarr_port}/api/v3'
			radarr_ssn = requests.Session()
			radarr_ssn.params.update({'apikey': radarr_api_token})
			try:
				movie_list = radarr_ssn.get(f'{radarr_base_url}/movie').json()
			except requests.exceptions.ConnectionError:
				return 'Can\'t connect to Radarr'

			#loop through all movies in radarr
			for movie in movie_list:
				if 'movieFile' in movie:
					if movie['movieFile']['mediaInfo']['videoCodec'] == codec:
						#movie matches codec; replace it
						print(movie['movieFile']['path'])
						#delete media file
						radarr_ssn.delete(f'{radarr_base_url}/movieFile/{movie["movieFile"]["id"]}')
						#start search for new file
						radarr_ssn.post(f'{radarr_base_url}/command', json={'name':'MoviesSearch', 'movieIds':[movie['id']]})
						result_json.append(movie['id'])
		else:
			return 'Radarr set as source but variables not set'

	return result_json

if __name__ == '__main__':
	import argparse

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Delete media files in sonarr/radarr that have the codec given and initiate a new search for them")
	parser.add_argument('-s', '--Source', type=str, choices=['sonarr','radarr'], help="Select the source which media files should be checked", required=True)
	parser.add_argument('-c', '--Codec', type=str, help="Media files with this codec will be removed and a new search will be initiated", required=True)

	args = parser.parse_args()
	#call function and process result
	response = remove_codec(source=args.Source, codec=args.Codec)
	if not isinstance(response, list):
		parser.error(response)
