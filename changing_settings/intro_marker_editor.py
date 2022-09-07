#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Edit the intro markers of plex media
Requirements (python3 -m pip install [requirement]):
	NO REQUIREMENTS
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	You can find the default location of your plex data directory here:
		https://support.plex.tv/articles/202915258-where-is-the-plex-media-server-data-directory-located/
"""

plex_data_directory = '/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/'

from datetime import datetime
from os import getenv
from os.path import join, isdir
from sqlite3 import connect, Row
from json import dumps

# Environmental Variables
plex_data_directory = getenv('plex_data_directory', plex_data_directory)

def intro_marker_editor(
	action: str,
	library_name: str, series_name: str, season_number: int=None, episode_number: int=None,
	intro_number: int=None, intro_begin: str=None, intro_end: str=None, intro_offset: int=None
):
	result_json = []

	#check for illegal arg parsing
	if not isdir(plex_data_directory):
		return 'The plex data directory could not be found'
	if not action in ('add','list','remove','edit','shift'):
		return 'Unknown action'
	if action == 'add' and not (intro_begin and intro_end):
		return 'Add requires a value for intro_begin and intro_end'
	if action == 'remove' and not (intro_number):
		return 'Remove requires a value for intro_number'
	if action == 'edit' and not (intro_number and intro_begin and intro_end):
		return 'Edit requires a value for intro_number, intro_begin and intro_end'
	if action == 'shift' and not (intro_number and intro_offset):
		return 'Shift requires a value for intro_number and intro_offset'
	if episode_number != None and season_number == None:
		return '"season_number" has to be set when "episode_number" is set'

	#create connection to plex database
	db = connect(join(plex_data_directory, 'Plug-in Support', 'Databases', 'com.plexapp.plugins.library.db'))
	row_cursor = db.cursor()
	db.row_factory = Row
	cursor = db.cursor()

	if action in ('edit','remove','shift') and intro_number:
		cursor.execute("SELECT id FROM taggings WHERE id = ?", (intro_number,))
		if cursor.fetchone() == None:
			return 'Intro number not found'

	#search for library
	row_cursor.execute("SELECT id FROM library_sections WHERE name = ? AND section_type = 2;", (library_name,))
	lib_id = next(iter(row_cursor.fetchone()), None)
	if lib_id == None:
		return 'Library not found or not a show library'

	row_cursor.execute("SELECT id FROM metadata_items WHERE library_section_id = ? AND title = ?", (lib_id, series_name))
	series_id = next(iter(row_cursor.fetchone()), None)
	if series_id == None:
		return 'Series not found'

	if season_number == None:
		#get all episodes in series
		cursor.execute("""
			WITH seasons
			AS (
				SELECT id, `index`
				FROM metadata_items
				WHERE metadata_type = 3
					AND parent_id = ?
				)
			SELECT
				title,
				(
					SELECT `index`
					FROM seasons
					WHERE id = parent_id
				) as season_number,
				`index` as episode_number,
				id
			FROM metadata_items
			WHERE metadata_type = 4
				AND (
					SELECT id
					FROM seasons
					WHERE id = parent_id
					)
			ORDER BY (
				SELECT `index`
				FROM seasons
				WHERE id = parent_id
				),
				`index`;
		""", (series_id,))
		episode_info = [dict(i) for i in cursor.fetchall()]
		if not episode_info:
			return 'Series is empty'

	elif episode_number == None:
		#get all episodes in a season of the series
		cursor.execute("""
			WITH seasons
			AS (
				SELECT id, `index`
				FROM metadata_items
				WHERE metadata_type = 3
				AND parent_id = ?
				AND `index` = ?
				)
			SELECT
				title,
				(
					SELECT `index`
					FROM seasons
					WHERE id = parent_id
				) as season_number,
				`index` as episode_number,
				id
			FROM metadata_items
			WHERE metadata_type = 4
				AND (
					SELECT id
					FROM seasons
					WHERE id = parent_id
					)
			ORDER BY `index`;
		""", (series_id, season_number))
		episode_info = [dict(i) for i in cursor.fetchall()]
		if not episode_info:
			return 'Season not found'

	elif episode_number != None:
		#get a specific episode of the series
		cursor.execute("""
			WITH seasons
			AS (
				SELECT id, `index`
				FROM metadata_items
				WHERE metadata_type = 3
					AND parent_id = ?
					AND `index` = ?
				)
			SELECT
				title,
				(
					SELECT `index`
					FROM seasons
					WHERE id = parent_id
				) as season_number,
				`index` as episode_number,
				id
			FROM metadata_items
			WHERE metadata_type = 4
				AND (
					SELECT id
					FROM seasons
					WHERE id = parent_id
					)
				AND `index` = ?;
		""", (series_id, season_number, episode_number))
		episode_info = [dict(i) for i in cursor.fetchall()]
		if not episode_info:
			return 'Episode not found'

	if action == 'add':
		intro_inserts = []
		for episode in episode_info:
			#convert timestamps given to ms
			if ':' in intro_begin:
				split_time = intro_begin.split(':')
				intro_begin = int(split_time[0]) * 60000 + int(split_time[1]) * 1000
			else:
				intro_begin = int(intro_begin)
			if ':' in intro_end:
				split_time = intro_end.split(':')
				intro_end = int(split_time[0]) * 60000 + int(split_time[1]) * 1000
			else:
				intro_end = int(intro_end)
			if intro_end < intro_begin:
				return 'End of intro is before begin of intro'
			#check for existing intros
			row_cursor.execute("""
				SELECT tag_id, `index`
				FROM taggings
				WHERE text = 'intro'
					AND metadata_item_id = ?
				ORDER BY `index` DESC
				LIMIT 1;
			""", (episode['id'],))
			result = row_cursor.fetchone()
			d = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			if result == None:
				#episode doesn't have intro yet
				cursor.execute("SELECT (SELECT tag_id AS main FROM taggings WHERE text = 'intro'), (SELECT tag_id + 1 AS alt FROM taggings ORDER BY tag_id DESC LIMIT 1);")
				i = cursor.fetchone()
				result = [i[0] or i[1], -1]
			intro_inserts.append((
				episode['id'],
				result[0],
				result[1] + 1,
				'intro',
				intro_begin,
				intro_end,
				'',
				d,
				'pv%3Aversion=5'
			))
		cursor.executemany("""
			INSERT INTO taggings(
				metadata_item_id,
				tag_id,
				`index`,
				text,
				time_offset,
				end_time_offset,
				thumb_url,
				created_at,
				extra_data
			) VALUES (
				?, ?, ?, ?, ?, ?, ?, ?, ?
			);
		""", intro_inserts)
		db.commit()

	elif action == 'shift':
		#get current timestamps
		row_cursor.execute("SELECT time_offset, end_time_offset FROM taggings WHERE id = ?", (intro_number,))
		timestamps = row_cursor.fetchone()
		cursor.execute("UPDATE taggings SET time_offset = ?, end_time_offset = ? WHERE id = ?", (timestamps[0] + (intro_offset * 1000), timestamps[1] + (intro_offset * 1000), intro_number))
		db.commit()

	elif action == 'edit':
		#convert timestamps given to ms
		if ':' in intro_begin:
			split_time = intro_begin.split(':')
			intro_begin = int(split_time[0]) * 60000 + int(split_time[1]) * 1000
		else:
			intro_begin = int(intro_begin)
		if ':' in intro_end:
			split_time = intro_end.split(':')
			intro_end = int(split_time[0]) * 60000 + int(split_time[1]) * 1000
		else:
			intro_end = int(intro_end)
		if intro_end < intro_begin:
			return 'End of intro is before begin of intro'

		cursor.execute("UPDATE taggings SET time_offset = ?, end_time_offset = ? WHERE id = ?", (intro_begin, intro_end, intro_number))
		db.commit()

	elif action == 'remove':
		cursor.execute("DELETE FROM taggings WHERE id = ?", (intro_number,))
		db.commit()

	#find the intro markers for each episode
	media_to_intro = {}
	for episode in episode_info:
		cursor.execute(f"""
			SELECT
				id AS intro_number,
				(
					SELECT (
						PRINTF('%02d',(time_offset / 1000 - time_offset / 1000 % 60) / 60))
						|| ':'
						|| PRINTF('%02d', (time_offset / 1000 % 60)
					)
				) AS intro_begin,
				(
					SELECT (
						PRINTF('%02d', (end_time_offset / 1000 - end_time_offset / 1000 % 60) / 60))
						|| ':'
						|| PRINTF('%02d', (end_time_offset / 1000 % 60)
					)
				) AS intro_end
			FROM taggings
			WHERE text = 'intro'
				AND metadata_item_id = ?
			ORDER BY `index`
		""", (episode['id'],))
		media_to_intro[episode['id']] = [dict(i) for i in cursor.fetchall()]
	for index, episode in enumerate(episode_info):
		episode['intros'] = media_to_intro.get(episode['id'], [])
		result_json.append(episode.pop('id'))
		episode_info[index] = episode

	print(dumps(episode_info, indent=4))

	return result_json

if __name__ == '__main__':
	from argparse import ArgumentParser

	#setup arg parsing
	parser = ArgumentParser(description='Edit the intro markers of plex media')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of the series library to target', required=True)
	parser.add_argument('-s','--SeriesName', type=str, help='Name of the series in the target library to target', required=True)
	parser.add_argument('-S','--SeasonNumber', type=int, help='Target a specific season inside the targeted series based on it\'s number (only accepted when -s is given) (specials is 0)')
	parser.add_argument('-e','--EpisodeNumber', type=int, help='Target a specific episode inside the targeted season based on it\'s number (only accepted when -S is given)')
	parser.add_argument('-a','--Action', help='The type of action you want to perform on the intro marker of the media', choices=('list','add','remove','edit','shift'), required=True)
	parser.add_argument('-n','--IntroNumber', type=int, help='REMOVE/EDIT/SHIFT ONLY: The number of the intro marker, shown when using -a list')
	parser.add_argument('-B','--IntroBegin', type=str, help='ADD/EDIT ONLY: The start of the intro marker. Supported formats are miliseconds and MM:SS')
	parser.add_argument('-E','--IntroEnd', type=str, help='ADD/EDIT ONLY: The end of the intro marker. Supported formats are miliseconds and MM:SS')
	parser.add_argument('-O','--IntroOffset', type=int, help='SHIFT ONLY: The amount to shift the intro marker in seconds (negative values supported)')

	args = parser.parse_args()
	#call function and process result
	response = intro_marker_editor(
		action=args.Action,
		library_name=args.LibraryName, series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber,
		intro_number=args.IntroNumber, intro_begin=args.IntroBegin, intro_end=args.IntroEnd, intro_offset=args.IntroOffset
	)
	if not isinstance(response, list):
		parser.error(response)
