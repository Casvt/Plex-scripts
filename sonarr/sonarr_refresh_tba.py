#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Refresh sonarr series for all TBA episodes
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script.
"""

sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''

from os import getenv

# Environmental Variables
sonarr_ip = getenv('sonarr_ip', sonarr_ip)
sonarr_port = getenv('sonarr_port', sonarr_port)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
base_url = f"http://{sonarr_ip}:{sonarr_port}/api/v3"

def sonarr_refresh_tba(ssn):
	result_json = []

	#find episodes that are TBA
	series_list = ssn.get(f'{base_url}/series').json()
	for series in series_list:
		series_output = ssn.get(f'{base_url}/episode', params={'seriesId': series['id']}).json()
		for episode in series_output:
			if episode['title'].lower() == 'tba':
				#episode found that is TBA
				print(f'{series["title"]}')

				#refresh episode
				ssn.post(f'{base_url}/command', json={'name': 'RefreshSeries','seriesId': series['id']})

				result_json.append(episode['id'])
				break

	return result_json

if __name__ == '__main__':
	from requests import Session

	#setup vars
	ssn = Session()
	ssn.params.update({'apikey': sonarr_api_token})

	#call function and process result
	response = sonarr_refresh_tba(ssn=ssn)
	if not isinstance(response, list):
		print(response)
