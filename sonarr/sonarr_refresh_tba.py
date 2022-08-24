#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Refresh sonarr- or plex series for all TBA episodes
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv

# Environmental Variables
sonarr_ip = getenv('sonarr_ip', sonarr_ip)
sonarr_port = getenv('sonarr_port', sonarr_port)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
sonarr_base_url = f"http://{sonarr_ip}:{sonarr_port}/api/v3"
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
plex_base_url = f'http://{plex_ip}:{plex_port}'

def sonarr_refresh_tba(sonarr_ssn, plex_ssn, target: list):
	result_json = []

	if 'sonarr' in target:
		#find episodes in sonarr that are TBA
		series_list = sonarr_ssn.get(f'{sonarr_base_url}/series').json()
		for series in series_list:
			series_output = sonarr_ssn.get(f'{sonarr_base_url}/episode', params={'seriesId': series['id']}).json()
			for episode in series_output:
				if episode['title'].lower() in ('tba','tbd'):
					#episode found that is TBA
					print(f'{series["title"]}')

					#refresh episode
					sonarr_ssn.post(f'{sonarr_base_url}/command', json={'name': 'RefreshSeries','seriesId': series['id']})

					result_json.append(episode['id'])
					break

	if 'plex' in target:
		#find episodes in plex that are TBA
		sections = plex_ssn.get(f'{plex_base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
		for lib in sections:
			if lib['type'] == 'show':
				#found show library; check every episode
				lib_content = plex_ssn.get(f'{plex_base_url}/library/sections/{lib["key"]}/all', params={'type': '4'}).json()['MediaContainer'].get('Metadata',[])
				for episode in lib_content:
					if episode['title'].lower() in ('tba','tbd'):
						#episode found that is TBA
						print(f'{episode["grandparentTitle"]} - S{episode["parentIndex"]}E{episode["index"]}')

						#refresh metadata of episode
						plex_ssn.put(f'{plex_base_url}/library/metadata/{episode["ratingKey"]}/refresh')

						result_json.append(episode['ratingKey'])

	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	#setup vars
	sonarr_ssn = Session()
	sonarr_ssn.params.update({'apikey': sonarr_api_token})
	plex_ssn = Session()
	plex_ssn.headers.update({'Accept': 'application/json'})
	plex_ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = ArgumentParser(description="Refresh sonarr- or plex series for all TBA episodes")
	parser.add_argument('-t','--Target', action='append', choices=['plex','sonarr'], required=True)

	args = parser.parse_args()
	#call function and process result
	response = sonarr_refresh_tba(sonarr_ssn=sonarr_ssn, plex_ssn=plex_ssn, target=args.Target)
	if not isinstance(response, list):
		print(response)
