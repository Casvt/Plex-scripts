#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Keep two libraries on a plex server synced
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every 20m or every 12h)
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def plex_library_sync(ssn, source_library_name: str, target_library_name: str, sync: list):
	result_json = []

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#get ids of the libraries
	source_lib_id, target_lib_id = '', ''
	for lib in sections:
		if lib['title'] == source_library_name:
			source_lib_id = lib['key']
		elif lib['title'] == target_library_name:
			target_lib_id = lib['key']
		elif source_lib_id and target_lib_id:
			break
	else:
		if not source_lib_id:
			return 'Source library not found'
		elif not target_lib_id:
			return 'Target library not found'
		else:
			return 'Something went wrong'

	source_lib_output = ssn.get(f'{base_url}/library/sections/{source_lib_id}/all', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']
	target_lib_output = ssn.get(f'{base_url}/library/sections/{target_lib_id}/all', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']

	if 'posters' in sync:
		print('Posters')
		#sync posters
		for media in source_lib_output:
			media_id = media.get('Guid', media.get('title', None))
			media_poster = media.get('thumb', None)
			if None in (media_id, media_poster): continue
			print(f'	{media["title"]}')

			#find media in target library
			for target_media in target_lib_output:
				if isinstance(media_id, list) and target_media.get('Guid', []) == media_id:
					#media found in target library
					target_ratingkey = target_media['ratingKey']
					break
				elif isinstance(media_id, str) and target_media.get('title', '') == media_id:
					#media found in target library
					target_ratingkey = target_media['ratingKey']
					break
			else:
				continue

			#upload poster
			ssn.post(f'{base_url}/library/metadata/{target_ratingkey}/posters', params={'url': f'{base_url}{media_poster}?X-Plex-Token={plex_api_token}'})
			result_json.append(media['ratingKey'])

	if 'collections' in sync:
		print('Collections')
		machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
		source_collections = ssn.get(f'{base_url}/library/sections/{source_lib_id}/collections').json()['MediaContainer'].get('Metadata', [])
		target_collections = ssn.get(f'{base_url}/library/sections/{target_lib_id}/collections').json()['MediaContainer'].get('Metadata', [])

		#remove all collections on the target server
		for col in target_collections:
			ssn.delete(f'{base_url}/library/collections/{col["ratingKey"]}')
		
		#sync all collections
		for col in source_collections:
			print(f'	{col["title"]}')
			#get the keys of the target media to put in the collection
			target_keys = []
			col_content = ssn.get(f'{base_url}{col["key"]}', params={'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])
			if not col_content: continue
			col_type = '1' if col_content[0]['type'] == 'movie' else '2'
			for source_media in col_content:
				media_id = source_media.get('Guid', source_media.get('title', None))
				if media_id == None: continue

				#find media in target library
				for target_media in target_lib_output:
					if isinstance(media_id, list) and target_media.get('Guid', []) == media_id:
						#media found in target library
						target_keys.append(target_media['ratingKey'])
						break
					elif isinstance(media_id, str) and target_media.get('title', '') == media_id:
						#media found in target library
						target_keys.append(target_media['ratingKey'])
						break
				result_json.append(source_media['ratingKey'])

			#create collection
			new_ratingkey = ssn.post(f'{base_url}/library/collections', params={'type': col_type, 'title': col['title'], 'smart': '0', 'sectionId': target_lib_id, 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(target_keys)}'}).json()['MediaContainer']['Metadata'][0]['ratingKey']
			#set poster
			if 'thumb' in col:
				ssn.post(f'{base_url}/library/collections/{new_ratingkey}/posters', params={'url': f'{base_url}{col["thumb"]}?X-Plex-Token={plex_api_token}'})
			#set info
			payload = {
				'type': '18',
				'id': new_ratingkey,
				'titleSort.value': col.get('titleSort', col.get('title','')),
				'contentRating.value': col.get('contentRating', ''),
				'summary.value': col.get('summary','')
			}
			ssn.put(f'{base_url}/library/sections/{target_lib_id}/all', params=payload)

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Keep two libraries on a plex server synced")
	parser.add_argument('-s', '--SourceLibraryName', type=str, help="Name of source library", required=True)
	parser.add_argument('-t', '--TargetLibraryName', type=str, help="Name of target library", required=True)
	parser.add_argument('-S', '--Sync', choices=['collections','posters'], action='append', default=[], required=True)

	args = parser.parse_args()
	#call function and process result
	response = plex_library_sync(ssn=ssn, source_library_name=args.SourceLibraryName, target_library_name=args.TargetLibraryName, sync=args.Sync)
	if not isinstance(response, list):
		parser.error(response)
