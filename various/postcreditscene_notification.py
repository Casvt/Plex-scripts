#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Get a notification when the media being watched has a post-credit scene
Requirements (python3 -m pip install [requirement]):
	requests
	apprise
Setup:
	1. Fill the plex variables below
	2. Setup the apprise_url below:
		Go to the following link, choose the service you want and add the url below.
		https://github.com/caronc/apprise/wiki#notification-services
		Example (email): apprise_url = 'mailto://example_user:example_password@gmail.com'
	3. Go to the tautulli web-ui -> Settings -> Notification Agents -> Add a new notification agent -> Script:
		Configuration:
			Script Folder = /path/to/script/folder
			Script File = select this script
			Script Timeout = 60
			Description = whatever you want
		Triggers:
			Playback Start = check
		Conditions:
			-- Parameter -- = Username
			-- Operator -- = is
			-- Value -- = your username
		Arguments:
			Playback Start -> Script Arguments = --RatingKey {rating_key}
"""

apprise_url = ''
plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from requests import get as requests_get
from re import search
from apprise import Apprise

# Environment Variables
apprise_url = getenv('apprise_url', apprise_url)
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f'http://{plex_ip}:{plex_port}'

def postcreditscene_notification(rating_key: str):
	result_json = []

	media_info = requests_get(f'{base_url}/library/metadata/{rating_key}', params={'X-Plex-Token': plex_api_token}, headers={'Accept': 'application/json'}).json()['MediaContainer']['Metadata'][0]
	title, year = media_info.get('originalTitle', media_info.get('title','')), media_info.get('year',0)
	search_results = requests_get(f'https://aftercredits.com/', params={'s': f'{title} {year}'}, headers={'Host': 'aftercredits.com','Referer': f'https://aftercredits.com/?s={title}+{year}'.replace(' ','+'), 'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"'}).text
	result = search(f'(?i)>(stingers|after credits)</a>            </div>\\r\\n            <h3 class=\"entry-title td-module-title\"><a href=\"[^\"]+?\" rel=\"bookmark\" title=\"{title} \({year}\)\*', search_results)
	if result:
		#media has post-credit scene
		print(f'{title} ({year}) has a post-credit scene')
		result_json.append(media_info['title'])

		app = Apprise()
		app.add(apprise_url)
		app.notify(
			body=f'The movie {title} ({year}) has a post-credit scene',
			title='A post-credit scene is coming up!'
		)

	return result_json

if __name__ == '__main__':
	from argparse import ArgumentParser

	#setup arg parsing
	parser = ArgumentParser(description='Get a notification when the media being watched has a post-credit scene')
	parser.add_argument('-k','--RatingKey', type=str, help='The rating key of the media to check', required=True)

	args = parser.parse_args()
	#call function and process result
	response = postcreditscene_notification(rating_key=args.RatingKey)
	if not isinstance(response, list):
		parser.error(response)
