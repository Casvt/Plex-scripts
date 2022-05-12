#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Make a playlist with the ondeck-episodes of certain series and keep the playlist updated so that it always the ondeck's
	Shuffle the playlist to basically watch your ondeck endlessly but shuffeled between your series
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below:
		The value of 'playlist_name' should be the name of the playlist that will be created/searched for.

		The on-decks of series will be maintained upon adding an episode of the series into the playlist.
		Example:
			I'm watching the show 'Avatar: The Last Airbender' and I'm at S01E03. I add any episode of the series
			to the playlist and next time the script is run (it should be run at an interval), the episode will be
			replaced with the on-deck episode (S01E03) and it will be maintained. You can do this with as many series
			as you want. When I've watched all episodes of the series, it get's removed from the playlist (as there
			is no on-deck episode anymore).

		Inside the 'series' variable, you can manually add the id's of series that you always want to check for.
		Example:
			You're watching a weekly show and you're up-to-date on the episodes. That means that when you've watched
			the most recent episode, there is no more episodes to watch so the script removes the series from the playlist.
			When a new episode comes out, it comes up again as an on-deck episode so it should be added to the playlist, but
			because the show was removed from the playlist a week earlier, it isn't "monitored" anymore. You can manually
			add the id of the series below in the list, which will enable the script to always monitor it for on-deck episodes
			eventhough it might not be in the playlist anymore.
		Guide:
			1. In the plex web-ui (ip:32400/web or app.plex.tv), go to the series info page (info about series, list of seasons, actors, etc.)
			2. Look in the url and locate "key=%2Flibrary%2Fmetadata%2F[DIGITS]"
			3. The "[DIGITS]" is the rating key of the series that you will need to add below
			EXAMPLE:
				url 1: key=%2Flibrary%2Fmetadata%2F583&context=
				url 2: key=%2Flibrary%2Fmetadata%2F1666&context=
				series = ["583", "1666"]
	
	Run the script at an interval (adviced to run the script every <6min)
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

series = []

from os import getenv

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
series = getenv('series', series)
base_url = f"http://{plex_ip}:{plex_port}"

def rolling_tv_channel(ssn, playlist_name: str='Rolling TV Channel'):
	result_json = []

	#get machine id of server
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	#get id of playlist if it exists
	playlists = ssn.get(f'{base_url}/playlists', params={'playlistType': 'video', 'includeCollections': '1'}).json()['MediaContainer']
	if 'Metadata' in playlists: playlists = playlists['Metadata']
	else: playlists = []
	for playlist in playlists:
		if playlist['title'] == playlist_name:
			#playlist found and ratingkey noted
			playlist_ratingkey = playlist['ratingKey']
			#pl entry -> on-deck
			series_mapping = {}
			#pl entry -> playlistItemID
			playlist_items = {}

			playlist_output = ssn.get(f'{base_url}/playlists/{playlist_ratingkey}/items').json()['MediaContainer']['Metadata']
			#determine the on-deck episode for every series inside the playlist
			for episode in playlist_output:
				if episode['type'] != 'episode': continue
				r = ssn.get(f'{base_url}/library/metadata/{episode["grandparentRatingKey"]}', params={'includeOnDeck': '1'}).json()['MediaContainer']['Metadata'][0]
				if 'OnDeck' in r.keys():
					series_mapping[episode['ratingKey']] = r['OnDeck']['Metadata']['ratingKey']
				else:
					series_mapping[episode['ratingKey']] = None

				playlist_items[episode['ratingKey']] = episode['playlistItemID']
				if episode['grandparentRatingKey'] in series:
					series.remove(episode['grandparentRatingKey'])
			#determine the on-deck episode for every series inside the list defined above
			for series_id in series:
				r = ssn.get(f'{base_url}/library/metadata/{series_id}', params={'includeOnDeck': '1'})
				if r.status_code != 404:
					r = r.json()['MediaContainer']['Metadata'][0]
					if 'OnDeck' in r.keys():
						series_mapping['None'] = r['OnDeck']['Metadata']['ratingKey']

			for episode_map in series_mapping.items():
				if episode_map[0] != 'None':
					#remove an episode from the playlist (either replace it with new on-deck or there is no on-deck anymore)
					ssn.delete(f'{base_url}/playlists/{playlist_ratingkey}/items/{playlist_items[episode_map[0]]}')
				if episode_map[1] != None:
					#add an episode to the playlist (either because it replaces the old on-deck or because a series just got a new episode)
					ssn.put(f'{base_url}/playlists/{playlist_ratingkey}/items', params={'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{episode_map[1]}'})
					result_json.append(episode_map[1])
			break
	else:
		#playlist doesn't exist yet so make one; fill it with the ondecks of the series-list (if it is populated)
		ondeck_ids = []
		for series_id in series:
			r = ssn.get(f'{base_url}/library/metadata/{series_id}', params={'includeOnDeck': '1'})
			if r.status_code != 404:
				series_data = r.json()['MediaContainer']['Metadata'][0]
				if 'OnDeck' in series_data.keys():
					ondeck_ids.append(series_data['OnDeck']['Metadata']['ratingKey'])
		ssn.post(f'{base_url}/playlists', params={'type': 'video', 'title': playlist_name, 'smart': '0', 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(ondeck_ids)}'})
		result_json = ondeck_ids

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Make a playlist with the ondeck-episodes of certain series and keep the playlist updated so that it always the ondeck\'s')
	parser.add_argument('-p','--PlaylistName', type=str, help='Name of target playlist', default='Rolling TV Channel')

	args = parser.parse_args()
	#call function and process result
	response = rolling_tv_channel(ssn=ssn, playlist_name=args.PlaylistName)
	if not isinstance(response, list):
		parser.error(response)
