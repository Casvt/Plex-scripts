#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Create a playlist with a series in it but with an alternate order coming from the tvdb
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = '192.168.2.15'
plex_port = '32400'
plex_api_token = 'QU4cw1mLdJjBjGMudSbF'

from os import getenv
import re

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def alternate_ordering_playlist(ssn, series_name: str, get_orders: bool=False, order: str=None, add_unknown: bool=False, no_watched: bool=False):
	result_json = []

	#check for illegal arg parsing
	if get_orders == False and order == None:
		return 'Neither "get_orders" or "order" are set'

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['type'] != 'show': continue

		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']
		for show in lib_output:
			if show['title'] == series_name:
				#show found
				show_guid = [g['id'] for g in show['Guid'] if g['id'].startswith('tvdb://')]
				if not show_guid:
					#tvdb id not found
					return 'The tvdb id of the series was not found'
				show_guid = show_guid[0].split('/')[-1]

				show_info = ssn.get(f'https://thetvdb.com/dereferrer/series/{show_guid}', params={}, headers={}).text
				seasons = re.search(r'<h2>Seasons</h2>\s+?<ul(.|\s)+?</ul', show_info).group(0)
				orders = re.findall(r'(?<=>)(?:\w| )+?(?=</a>)', seasons)
				links = [b.split('"')[-1] for b in re.findall(r'<ul class="list-group list-group-condensed mb-1">.*?<a href=".*?(?=">)', show_info, re.DOTALL)]
				for index, link in enumerate(links):
					if link.startswith('/'):
						links[index] = f'https://thetvdb.com{link}'

				if get_orders == True:
					#user requests orders
					return orders
				if not order in orders:
					#order user gave is not found
					return 'Order not found'

				for index, order_entry in enumerate(orders):
					if order_entry == order:
						link = links[index]
						break
				else:
					return 'Order not found'

				#get all episodes of series in the order specified and note tvdb ids in order
				show_content = ssn.get(link, params={}, headers={}).text
				tvdb_ids = [x.split('/')[-1] for x in re.findall(r'episode-label".*?/episodes/\d+', show_content, re.DOTALL)]

				#create a map: tvdb id -> plex rating key
				id_map = {}
				show_content = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']
				for episode in show_content:
					if no_watched == True and 'viewCount' in episode:
						continue
					if not 'Guid' in episode: episode['Guid'] = []
					for id in episode['Guid']:
						if id['id'].startswith('tvdb://'):
							id_map[id['id'].split('/')[-1]] = episode['ratingKey']
							break
					else:
						if '_none' in id_map:
							id_map['_none'].append(episode['ratingKey'])
						else:
							id_map['_none'] = [episode['ratingKey']]

				#create list of episodes ratingkeys in order of tvdb order
				for tvdb_id in tvdb_ids:
					if tvdb_id in id_map:
						result_json.append(id_map[tvdb_id])
				if add_unknown == True and '_none' in id_map:
					result_json += id_map['_none']

				#if playlist with this name already exists, remove it first
				playlists = ssn.get(f'{base_url}/playlists').json()['MediaContainer']
				if 'Metadata' in playlists:
					for playlist in playlists['Metadata']:
						if playlist['title'] == f'{show["title"]} - {order}':
							ssn.delete(f'{base_url}/playlists/{playlist["ratingKey"]}')

				#create playlist
				machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
				ssn.post(f'{base_url}/playlists', params={'type': 'video', 'title': f'{show["title"]} - {order}', 'smart': '0', 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(result_json)}'})

				break
		else:
			continue
		break
	else:
		return 'Series not found'

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Create a playlist with a series in it but with an alternate order coming from the tvdb")
	parser.add_argument('-s', '--SeriesName', type=str, help="Target a specific series inside a show library based on it's name", required=True)
	parser.add_argument('-g', '--GetOrders', help="Get the tvdb orders available for the series", action='store_true')
	parser.add_argument('-o', '--Order', type=str, help="Name of tvdb order that should be applied")
	parser.add_argument('-u', '--AddUnknown', help="Add all episodes of the show that weren't found in the tvdb to the end of the playlist", action='store_true')
	parser.add_argument('-w', '--NoWatched', help="Don't add episodes that are marked as watched", action='store_true')

	args = parser.parse_args()
	#call function and process result
	response = alternate_ordering_playlist(ssn=ssn, series_name=args.SeriesName, get_orders=args.GetOrders, order=args.Order, add_unknown=args.AddUnknown, no_watched=args.NoWatched)
	if isinstance(response, list):
		if args.GetOrders == True:
			#the orders of the series was requested so print them out
			for order in response:
				print(order)
	else:
		if response == 'Neither "get_orders" or "order" are set':
			parser.error('Neither -g/--GetOrders or -o/--Order was given')
		else:
			parser.error(response)
