#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Add a keyword to the genre list in plex if the keyword is present in the keyword list of the media on the IMDB
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv
from re import findall as re_findall
from fnmatch import filter as fnmatch_filter

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

def keywords_to_genre(ssn, keywords: list, library_names: list, movie_names: list=[], series_names: list=[], skip_locked: bool=False):
	result_json = []

	for library_name in library_names:
		#find library
		sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
		lib_id, lib_type = next(iter([[lib['key'],lib['type']] for lib in sections if lib['title'] == library_name]), ['',''])
		if not lib_id: return 'Library not found'

		#check for illegal arg parsing
		if lib_type == 'movie' and series_names: return 'Library is a movie library but "series_names" is set'
		elif lib_type == 'show' and movie_names: return 'Library is a show library but "movie_names" is set'
		elif not lib_type in ('movie','show'): return 'Invalid library type'

		#go through every entry in the library
		lib_output = ssn.get(f'{base_url}/library/sections/{lib_id}/all', params={'includeGuids': '1'}).json()['MediaContainer']['Metadata']
		for media in lib_output:
			#skip if media is not selected
			if (movie_names and not media['title'] in movie_names) or (series_names and not media['title'] in series_names): continue

			media_output = ssn.get(f'{base_url}/library/metadata/{media["ratingKey"]}').json()['MediaContainer']['Metadata'][0]
			#skip if genre field is locked and skip_locked is True
			if skip_locked == True and [l for l in media_output.get('Field', []) if l['name'] == 'genre' and l['locked'] == True]: continue

			#find imdb id of media otherwise skip
			media_guid = next(iter([guid['id'].split('/')[-1] for guid in media.get('Guid',[]) if guid['id'].startswith('imdb://')]), '')
			if not media_guid: continue

			#get all genres that media has been tagged with
			media_genres = {str(i): g['tag'] for i, g in enumerate(media_output.get('Genre', []))}

			#get all keywords that media has on imdb
			media_info = ssn.get(f'https://www.imdb.com/title/{media_guid}/keywords').text
			media_keywords = re_findall(r'(?<=data-item-keyword=").*?(?=")', media_info)

			#go through every target keyword and if it's in the list (but not already in the genre list), add it to the genres
			new_genres = []
			media_genres_values = media_genres.values()
			for k in keywords:
				if '*' in k:
					result = fnmatch_filter(media_keywords, k)
					new_genres += [r for r in result if not r in media_genres_values]
				else:
					if k in media_keywords and not k in media_genres_values:
						new_genres.append(k)

			#upload new genres
			payload = {
				'type': '2' if media['type'] == 'show' else '1',
				'id': media['ratingKey'],
				'genre.locked': '1',
				**{f'genre[{i}].tag.tag': g for i, g in list(media_genres.items()) + list(zip(range(len(media_genres), len(media_genres) + len(new_genres)), new_genres))}
			}
			ssn.put(f'{base_url}/library/sections/{lib_id}/all', params=payload)

			result_json.append(media['ratingKey'])

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Add a keyword to the genre list in plex if the keyword is present in the keyword list of the media on the IMDB')
	parser.add_argument('-k','--Keyword', type=str, help='Keyword that will be added to genre list if found in keyword list; allowed to give multiple times; supports wildcards (*)', action='append', required=True)
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library; allowed to give multiple times', action='append', required=True)
	parser.add_argument('-m','--MovieName', type=str, help='Name of target movie; allowed to give multiple times (requires -l to be a movie library)', action='append', default=[])
	parser.add_argument('-s','--SeriesName', type=str, help='Name of target series; allowed to give multiple times (requires -l to be a show library)', action='append', default=[])
	parser.add_argument('-S','--SkipLocked', help='Skip media that has it\'s genre field locked', action='store_true')

	args = parser.parse_args()
	#call function and process result
	response = keywords_to_genre(ssn=ssn, keywords=args.Keyword, library_names=args.LibraryName, movie_names=args.MovieName, series_names=args.SeriesName, skip_locked=args.SkipLocked)
	if not isinstance(response, list):
		if response == 'Library is a movie library but "series_names" is set':
			parser.error('Library is a movie library but -s/--SeriesName is set')
		elif response == 'Library is a show library but "movie_names" is set':
			parser.error('Library is a show library but -m/--MovieName is set')
		else:
			parser.error(response)
