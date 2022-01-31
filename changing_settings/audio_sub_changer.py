#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Change the audio/subtitle track, based on target language, for an episode, season, series, movie or entire movie/show library
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script.
	Check the help page (python3 audio_sub_changer.py --help) to see how to use the script with it's arguments.
	You can find examples of the usage at the bottom of the help page.
	When the script is run with it's arguments, it will show you what media it has processed and will let you know for what media it has changed and for which users
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests, argparse

def episode(episode_id, media_type="show"):
	for token in users:
		episode_output = requests.get(baseurl + '/library/metadata/' + str(episode_id), params={'X-Plex-Token': token}, headers={'Accept': 'application/json'}).json()
		part_db = {}
		if media_type == "show" and token == users[0]:
			print(episode_output['MediaContainer']['Metadata'][0]['grandparentTitle'] + ' - S' + str(episode_output['MediaContainer']['Metadata'][0]['parentIndex']) + 'E' + str(episode_output['MediaContainer']['Metadata'][0]['index']) + ' - ' + str(episode_output['MediaContainer']['Metadata'][0]['title']))
		elif media_type == "movie" and token == user[0]:
			print(episode_output['MediaContainer']['Metadata'][0]['title'])
		for media in episode_output['MediaContainer']['Metadata'][0]['Media']:
			for part in media['Part']:
				selected_stream = ''
				for stream in part['Stream']:
					if stream['streamType'] == args.Type and 'selected' in stream.keys() and 'languageTag' in stream.keys() and stream['languageTag'] == args.Language:
						selected_stream = stream
						break
				part_db[part['id']] = {
					'part': part,
					'selected_stream': selected_stream
				}
		for part in part_db.keys():
			for stream in part_db[part]['part']['Stream']:
				if stream['streamType'] == args.Type and 'languageTag' in stream.keys() and stream['languageTag'] == args.Language and not part_db[part]['selected_stream']:
					if args.Type == 2:
						requests.put(baseurl + '/library/parts/' + str(part), params={'audioStreamID': stream['id'], 'allParts': 1, 'X-Plex-Token': token})
					elif args.Type == 3:
						requests.put(baseurl + '/library/parts/' + str(part), params={'subtitleStreamID': stream['id'], 'allParts': 1, 'X-Plex-Token': token})
					print(f'	Edited for {users_name[token]}')
					break

#setup variables
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
baseurl = 'http://' + plex_ip + ':' + plex_port
section_output = ssn.get(baseurl + '/library/sections').json()
langs = ['aa', 'ab', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'br', 'bs', 'ca', 'ce', 'ch', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv', 'dz', 'ee', 'el', 'en', 'en-US', 'en-GB', 'en-AU', 'eo', 'es', 'et', 'eu', 'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz', 'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky', 'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my', 'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps', 'pt', 'qu', 'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty', 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo', 'wa', 'wo', 'xh', 'yi', 'yo', 'za', 'zh', 'zu']

#handle argument parsing
parser = argparse.ArgumentParser(
	formatter_class=argparse.RawDescriptionHelpFormatter,
	description="Change the audio/subtitle track, based on target language, for an episode, season, series, movie or entire movie/show library\n\n\
You can narrow down the media that is processed (normally the complete library) by specifying the series, season or even specific episode that you want to process for a show library,\n\
or a movie for a movie library. If you've selected a movie library, you can parse the -m/--Movie argument multiple times to process multiple movies.",
	epilog=f"Examples:\n\
	python3 {__file__} --Type audio --Language fr --LibraryName Tv-series\n\
		Try to set the audio for all episodes of all series in the 'Tv-series' library to one with the language French\n\
	python3 {__file__} --Type subtitle --Language en --LibraryName Tv-series --Series 'Initial D' --SeasonNumber 5\n\
		Try to set the subtitle for Tv-series->Initial D->S05 to one with the language English\n\
	python3 {__file__} --Type subtitle --Language en --LibraryName Films --Movie '2 Fast 2 Furious' --Movie 'The Fast and The Furious'\n\
		Try to set the subtitle for Films->2 Fast 2 Furious AND ALSO Films->The Fast and The Furious to one with the language English"
)
parser.add_argument('-t', '--Type', choices=['audio','subtitle'], help="Give the type of stream to change", required=True)
parser.add_argument('-l', '--Language', type=str, help="ISO-639-1 (2 lowercase letters) language code (e.g. en) to try to set the stream to", required=True)
parser.add_argument('-L', '--LibraryName', type=str, help="Name of target library", required=True)
parser.add_argument('-S', '--Series', type=str, help="Target series name")
parser.add_argument('-s', '--SeasonNumber', type=int, help="Target Season number")
parser.add_argument('-e', '--EpisodeNumber', type=int, help="Target Episode number")
parser.add_argument('-m', '--Movie', type=str, help="Target movie; allowed to give argument multiple times", action='append')
parser.add_argument('-u', '--User', type=str, help="Select the user(s) to apply this to; Give username, '@me' for yourself or '@all' for everyone", action='append')
args = parser.parse_args()
if args.Type == 'audio': args.Type = 2
elif args.Type == 'subtitle': args.Type = 3
if not args.Language in langs: parser.error('-l/--Language requires a valid language code')
if isinstance(args.SeasonNumber, int) and (args.Series == None): parser.error('-s/--SeasonNumber requires -S/--Series')
if isinstance(args.EpisodeNumber, int) and (args.Series == None or args.SeasonNumber == None): parser.error('-e/--EpisodeNumber requires -S/--Series and -s/--SeasonNumber')
for level in section_output['MediaContainer']['Directory']:
	if level['title'] == args.LibraryName and level['type'] in ('show','movie'):
		args.LibraryName = level['key']
		break
else: parser.error('Library not found')
if args.Series != None:
	for level in ssn.get(baseurl + '/library/sections/' + args.LibraryName + '/all').json()['MediaContainer']['Metadata']:
		if level['title'] == args.Series:
			args.Series = level['ratingKey']
			break
	else: parser.error('Series not found')
if args.SeasonNumber != None:
	for level in ssn.get(baseurl + '/library/metadata/' + args.Series + '/children').json()['MediaContainer']['Metadata']:
		if level['index'] == args.SeasonNumber:
			args.SeasonNumber = level['ratingKey']
			break
	else: parser.error('Season not found')
if args.EpisodeNumber != None:
	for level in ssn.get(baseurl + '/library/metadata/' + args.SeasonNumber + '/children').json()['MediaContainer']['Metadata']:
		if level['index'] == args.EpisodeNumber:
			args.EpisodeNumber = level['ratingKey']
			break
	else: parser.error('Episode not found')
users = []
users_name = {}
if args.User == None:
	users = [plex_api_token]
	users_name = {plex_api_token: 'yourself'}
else:
	import re
	user_share_output = requests.get('http://plex.tv/api/servers/' + ssn.get(baseurl + '/').json()['MediaContainer']['machineIdentifier'] + '/shared_servers', params={'X-Plex-Token': plex_api_token}).text
	if '@all' in args.User:
		for user_data in re.findall('(?<=username=").*accessToken=".*?(?=" )', user_share_output):
			user_token = str(re.search('[^"]+$', user_data).group(0))
			users.append(user_token)
			users_name[user_token] = str(re.search('^.*?(?=" )', user_data).group(0))
	else:
		for user in args.User:
			if user == '@me':
				users.append(plex_api_token)
				users_name[plex_api_token] = 'yourself'
				continue
			else:
				try:
					pre_user_token = str(re.search('(?<=username="' + user + '").*accessToken=".*?(?=")', user_share_output).group(0))
					user_token = str(re.search('[^"]+$', pre_user_token).group(0))
					users.append(user_token)
					users_name[user_token] = str(re.search('^.*?(?=" )', user_data).group(0))

				except AttributeError:
					parser.error(f'{user} not found on server')

#edit the media
if args.EpisodeNumber != None:
	#change an episode
	episode(args.EpisodeNumber)
elif args.SeasonNumber != None:
	#change a season
	for episodes in ssn.get(baseurl + '/library/metadata/' + args.SeasonNumber + '/children').json()['MediaContainer']['Metadata']:
		episode(episodes['ratingKey'])
elif args.Series != None:
	#change a series
	for episodes in ssn.get(baseurl + '/library/metadata/' + args.Series + '/allLeaves').json()['MediaContainer']['Metadata']:
		episode(episodes['ratingKey'])
else:
	lib_output = ssn.get(baseurl + '/library/sections/' + args.LibraryName + '/all').json()
	if lib_output['MediaContainer']['Metadata'][0]['type'] == 'show':
		#change a complete show library
		for show in lib_output['MediaContainer']['Metadata']:
			for episodes in ssn.get(baseurl + '/library/metadata/' + show['ratingKey'] + '/allLeaves').json()['MediaContainer']['Metadata']:
				episode(episodes['ratingKey'])
	elif lib_output['MediaContainer']['Metadata'][0]['type'] == 'movie':
		#change a complete movie library
		if args.Series != None or args.SeasonNumber != None or args.EpisodeNumber != None:
			parser.error('Library is a movie library but show-arguments were given')
		for movie in lib_output['MediaContainer']['Metadata']:
			if args.Movie != None and not str(movie['title']) in args.Movie: continue
			episode(movie['ratingKey'], media_type="movie")
	else:
		parser.error('Library is not a show or movie library')
