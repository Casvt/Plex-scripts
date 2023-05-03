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
from re import compile
from fnmatch import filter as fnmatch_filter
from typing import List

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"
keyword_finder = compile(r'(?<=data-item-keyword=").*?(?=")')

def keywords_to_genre(
	ssn,
	keywords: List[str],
	library_names: List[str],
	movie_names: List[str]=[],
	series_names: List[str]=[],
	skip_locked: bool=False
) -> List[int]:
	result_json = []

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory', [])
	for lib in sections:
		if not lib['title'] in library_names:
			continue
		
		# Check for illegal arg parsing
		if not lib['type'] in ('movie','show'): return 'Invalid library type'
		
		lib_output: List[dict] = ssn.get(
			f'{base_url}/library/sections/{lib["key"]}/all',
			params={'includeGuids': '1'}
		).json()['MediaContainer'].get('Metadata', [])

		for media in lib_output:
			if ((lib['type'] == 'movie' and movie_names and not media['title'] in movie_names)
       		or (lib['type'] == 'show' and series_names and not media['title'] in series_names)):
				continue
			
			media_output: dict = ssn.get(
				f'{base_url}/library/metadata/{media["ratingKey"]}'
			).json()['MediaContainer']['Metadata'][0]
			
			# Skip media if genre field is locked and skip_locked is True
			if skip_locked:
				if any(l['name'] == 'genre' and l['locked'] for l in media_output.get('Field', [])):
					continue

			# Find IMDB id of media otherwise skip
			for guid in media.get('Guid', []):
				if guid['id'].startswith('imdb://'):
					media_guid = guid['id'].split('/')[-1]
					break
			else:
				continue
			
			# Get all genres that media has been tagged with
			media_genres = [g['tag'] for g in media_output.get('Genre', [])]
			
			# Get all keywords that media has on IMDB
			imdb_info = ssn.get(f'https://www.imdb.com/title/{media_guid}/keywords').text
			media_keywords = keyword_finder.findall(imdb_info)

			# Find keywords that are desired to be added but aren't already
			new_genres = []
			for k in keywords:
				if '*' in k:
					result = fnmatch_filter(media_keywords, k)
					new_genres += [r for r in result if not r in media_genres]
				else:
					if k in media_keywords and not k in media_genres:
						new_genres.append(k)
						
			# Push new genres
			payload = {
				'type': '2' if media['type'] == 'show' else '1',
				'id': media['ratingKey'],
				'genre.locked': '1',
				**{f'genre[{c}].tag.tag': v for c, v in enumerate(media_genres + new_genres)}
			}
			ssn.put(f'{base_url}/library/sections/{lib["key"]}/all', params=payload)
			
			result_json.append(media['ratingKey'])
	return result_json

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser

	# Setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	# Setup arg parsing
	parser = ArgumentParser(description='Add a keyword to the genre list in plex if the keyword is present in the keyword list of the media on the IMDB')
	parser.add_argument('-k','--Keyword', type=str, help='Keyword that will be added to genre list if found in keyword list; allowed to give multiple times; supports wildcards (*)', action='append', required=True)
	parser.add_argument('-l','--LibraryName', type=str, help='Name of target library; allowed to give multiple times', action='append', required=True)
	parser.add_argument('-m','--MovieName', type=str, help='Name of target movie; allowed to give multiple times', action='append', default=[])
	parser.add_argument('-s','--SeriesName', type=str, help='Name of target series; allowed to give multiple times', action='append', default=[])
	parser.add_argument('-S','--SkipLocked', help='Skip media that has it\'s genre field locked', action='store_true')

	args = parser.parse_args()
	# Call function and process result
	response = keywords_to_genre(
		ssn=ssn, keywords=args.Keyword,
		library_names=args.LibraryName,
		movie_names=args.MovieName,
		series_names=args.SeriesName,
		skip_locked=args.SkipLocked
	)
	if not isinstance(response, list):
		if response == 'Library is a movie library but "series_names" is set':
			parser.error('Library is a movie library but -s/--SeriesName is set')
		elif response == 'Library is a show library but "movie_names" is set':
			parser.error('Library is a show library but -m/--MovieName is set')
		else:
			parser.error(response)
