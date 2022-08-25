#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script:
	Create a version of the media poster with a banner at the top containing chosen information and upload it to plex
Requirements (python3 -m pip install [requirement]):
	Pillow
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
Note:
	There is an accompanying file called 'poster_banner.otf' that should also be downloaded and be put in the same folder as the script. This file can be found in the repository too.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import os
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw

# Environment variables
plex_ip = os.getenv('plex_ip', plex_ip)
plex_port = os.getenv('plex_port', plex_port)
plex_api_token = os.getenv('plex_api_token', plex_api_token)
base_url = f'http://{plex_ip}:{plex_port}'

def _set_poster(ssn, rating_key: str, info: str, position: str='top', background: str='black', background_transparency: int=0.65):
	font_file = os.path.join(os.path.dirname(__file__), 'poster_banner.otf')
	font_size = 500

	media_info = ssn.get(f'{base_url}/library/metadata/{rating_key}').json()['MediaContainer']['Metadata'][0]
	if not 'thumb' in media_info: return

	#check for illegal arg parsing and get content
	content = ''
	if media_info['type'] in ('movie','episode'):
		if info in ('title', 'studio', 'year'):
			content = media_info[info]
		elif info == 'content_rating':
			content = media_info['contentRating']
		elif info == 'resolution':
			content = media_info['Media'][0]['videoResolution']
			if content.isdigit(): content += 'p'
		elif info == 'video_codec':
			content = media_info['Media'][0]['videoCodec']
		else:
			if media_info['type'] == 'movie': return 'Invalid info type for "movie"'
			elif media_info['type'] == 'episode': return 'Invalid info type for "episode"'

	elif media_info['type'] == 'show':
		if info in ('title', 'studio', 'year'):
			content = media_info[info]
		elif info == 'content_rating':
			content = media_info['contentRating']
		elif info == 'status':
			if not 'Guid' in media_info: return 'No tvdb id found of media'
			for guid in media_info['Guid']:
				if guid['id'].startswith('tvdb://'):
					from re import search as re_search
					tvdb_info = ssn.get(f'https://thetvdb.com/dereferrer/series/{guid["id"].split("/")[-1]}').text
					try:
						content = re_search(r'<strong>Status</strong>\r\n\s+<span>\r\n.*?\w+', tvdb_info).group(0).split(' ')[-1]
					except Exception:
						return 'Failed to get series status'
					break
			else:
				return 'No tvdb id found of media'
		else:
			return 'Invalid info type for "show"'

	if content:
		content = str(content)
	else:
		return 'Invalid media type'

	#download current poster
	poster_data = ssn.get(f'{base_url}{media_info["thumb"]}').content

	#create PIL instance of poster and calculate info
	source_img = Image.open(BytesIO(poster_data)).convert("RGBA")
	img_width, img_height = source_img.size
	if position == 'top': bar_size = ((0, 0), (img_width, img_height * 0.1))
	if position == 'bottom': bar_size = ((0, img_height * 0.9), (img_width, img_height))
	#keep decreasing fontsize until content fits
	for size in range(font_size, 0, -1):
		font = ImageFont.truetype(font_file, size)
		text_px = font.getsize(content)
		if text_px[0] > bar_size[1][0] * 0.9 and size > 1: continue
		if position == 'top':
			if text_px[1] > bar_size[1][1] * 0.9 and size > 1: continue
			text_size = ((img_width / 2) - (text_px[0] / 2), (bar_size[1][1] / 2) - (text_px[1] / 2 ))
		elif position == 'bottom':
			if text_px[1] > (img_height - bar_size[0][1]) * 0.9 and size > 1: continue
			text_size = ((img_width / 2) - (text_px[0] / 2), ((bar_size[0][1]) + ((img_height - bar_size[0][1]) / 2)) - (text_px[1] / 2 ))
		break
	#determine background and text color
	if background == 'black':
		bar_color = "black"
	elif background == 'semi-transparent':
		bar_color = (0,0,0, int(255 * background_transparency))

	#draw ractangle
	if background == "black":
		draw = ImageDraw.Draw(source_img)
		draw.rectangle(bar_size, fill=bar_color)
	elif background == "semi-transparent":
		overlay = Image.new("RGBA", source_img.size, (0,0,0,0))
		overlay_draw = ImageDraw.Draw(overlay)
		overlay_draw.rectangle(bar_size, fill=bar_color)
		source_img = Image.alpha_composite(source_img, overlay)
		draw = ImageDraw.Draw(source_img)
	#put text inside
	draw.text(text_size, content, font=font, fill="white")

	#save edited version
	output_image = BytesIO()
	source_img.convert("RGB").save(output_image, 'jpeg')

	#upload new poster
	ssn.post(f'{base_url}/library/metadata/{rating_key}/posters', data=output_image.getvalue())

	return

def poster_banner(ssn, info: str, library_name: str, movie_name: list=[], series_name: str=None, target: str=None, season_number: int=None, episode_number: int=None, position: str='top', background: str='black', background_transparency: int=0.65):
	result_json = []

	#check for illegal arg parsing
	if series_name != None and target == None:
		#series name is given but no target
		return '"series_name" is set but not "target"'
	if target != None and not target in ('series', 'episode'):
		#target is set but with invalid value
		return 'Invalid value for "target"'
	if season_number != None and series_name == None:
		#season number given but no series name
		return '"season_number" is set but not "series_name"'
	if episode_number != None and (season_number == None or series_name == None):
		#episode number given but no season number or no series name
		return '"episode_number" is set but not "season_number" or "series_name"'
	if not position in ('top','bottom'):
		#position is set but with invalid value
		return 'Invalid value for "position"'

	sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer']['Directory']
	#loop through the libraries
	for lib in sections:
		if lib['title'] != library_name: continue

		#this library is targeted
		print(lib['title'])
		lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all').json()['MediaContainer']['Metadata']
		if lib['type'] == 'movie':
			#library is a movie lib; loop through every movie
			for movie in lib_output:
				if movie_name and not movie['title'] in movie_name:
					#a specific movie is targeted and this one is not it, so skip
					continue

				print(f'	{movie["title"]}')
				result = _set_poster(ssn=ssn, rating_key=movie['ratingKey'], info=info, position=position, background=background, background_transparency=background_transparency)
				if result == None: result_json.append(movie['ratingKey'])
				else: return result

		elif lib['type'] == 'show':
			#library is show lib; loop through every show
			for show in lib_output:
				if series_name != None and show['title'] != series_name:
					#a specific show is targeted and this one is not it, so skip
					continue

				print(f'	{show["title"]}')
				if target == 'series':
					result = _set_poster(ssn=ssn, rating_key=show['ratingKey'], info=info, position=position, background=background, background_transparency=background_transparency)
					if result == None: result_json.append(show['ratingKey'])
					else: return result
				elif target == 'episode':
					show_output = ssn.get(f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves').json()['MediaContainer']['Metadata']
					#loop through episodes of show to check if targeted season exists
					if season_number != None:
						for episode in show_output:
							if episode['parentIndex'] == season_number:
								break
						else:
							return 'Season not found'
					#loop through episodes of show
					for episode in show_output:
						if season_number != None and episode['parentIndex'] != season_number:
							#a specific season is targeted and this one is not it; so skip
							continue

						if episode_number != None and episode['index'] != episode_number:
							#this season is targeted but this episode is not; so skip
							continue

						print(f'		S{episode["parentIndex"]}E{episode["index"]}	- {episode["title"]}')
						result = _set_poster(ssn=ssn, rating_key=episode['ratingKey'], info=info, position=position, background=background, background_transparency=background_transparency)
						if result == None: result_json.append(episode['ratingKey'])
						else: return result

						if episode_number != None:
							#the targeted episode was found and processed so exit loop
							break
					else:
						if episode_number != None:
							#the targeted episode was not found
							return 'Episode not found'

				if series_name != None:
					#the targeted series was found and processed so exit loop
					break
			else:
				if series_name != None:
					#the targeted series was not found
					return 'Series not found'
		else:
			return 'Library not supported'
		#the targeted library was found and processed so exit loop
		break
	else:
		#the targeted library was not found
		return 'Library not found'

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	parser = argparse.ArgumentParser(description="Create a version of the media poster with a banner at the top containing chosen information and upload it to plex")
	parser.add_argument('-i', '--Info', choices=['title','studio','year','content_rating','status','resolution','video_codec'], help="The info that should be put inside the bar", required=True)
	parser.add_argument('-p', '--Position', choices=['top','bottom'], help='The location of the black bar on the poster', default='top')
	parser.add_argument('-b', '--Background', choices=['black','semi-transparent'], help='Choose the background of the banner', default='black')
	parser.add_argument('-T', '--BackgroundTransparency', type=int, help='Choose how transparent the background is when -b/--Background is set to "semi-transparent". Should be between 0 and 1. Default is 0.65', default=0.65)
	parser.add_argument('-l', '--LibraryName', type=str, help="Name of target library", required=True)
	parser.add_argument('-m', '--MovieName', type=str, help="Target a specific movie inside a movie library based on it's name (only accepted when -l is a movie library); allowed to give argument multiple times", action='append', default=[])
	parser.add_argument('-s', '--SeriesName', type=str, help="Target a specific series inside a show library based on it's name (only accepted when -l is a show library)")
	parser.add_argument('-t', '--Target', choices=['series','episode'], help="When a series is selected, should the series poster be changed or the posters of the episodes inside it?")
	parser.add_argument('-S', '--SeasonNumber', type=int, help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given) (specials is 0)")
	parser.add_argument('-e', '--EpisodeNumber', type=int, help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given)")

	args = parser.parse_args()
	#call function and process result
	response = poster_banner(ssn=ssn, info=args.Info, position=args.Position, background=args.Background, background_transparency=args.BackgroundTransparency, library_name=args.LibraryName, movie_name=args.MovieName, series_name=args.SeriesName, target=args.Target, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber)
	if not isinstance(response, list):
		if response == '"series_name" is set but not "target"':
			parser.error('-s/--SeriesName given but not -t/--Target given')

		elif response == '"season_number" is set but not "series_name"':
			parser.error('-S/--SeasonNumber given but not -s/--SeriesName given')

		elif response == '"episode_number" is set but not "season_number" or "series_name"':
			parser.error('-e/--EpisodeNumber given but -S/--SeasonNumber or -s/--SeriesName not given')

		else:
			parser.error(response)
