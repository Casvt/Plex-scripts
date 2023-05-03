#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Edit the intro markers of plex media.
	Requires script to be run with root (a.k.a. administrator) privileges
Requirements (python3 -m pip install [requirement]):
	NO REQUIREMENTS
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	You can find the default location of your plex data directory here:
		https://support.plex.tv/articles/202915258-where-is-the-plex-media-server-data-directory-located/
"""

plex_data_directory = '/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/'

from datetime import datetime
from json import dumps
from os import getenv
from os.path import isdir, isfile, join
from sqlite3 import Row, connect
from typing import List, Union

# Environmental Variables
plex_data_directory = getenv('plex_data_directory', plex_data_directory)

actions = ('add','list','remove','edit','shift')

def _get_episodes(
	cursor,
	series_id: int, season_number: int=None, episode_number: int=None
) -> Union[List[dict], str]:
	if season_number is None:
		# Get all episodes in series
		cursor.execute("""
			WITH seasons
			AS (
				SELECT
					id,
					`index` AS season_number
				FROM metadata_items
				WHERE
					metadata_type = 3
					AND parent_id = ?
				)
			SELECT
				title,
				season_number,
				`index` AS episode_number,
				mi.id
			FROM metadata_items mi
			INNER JOIN seasons s
			ON mi.parent_id = s.id
			WHERE metadata_type = 4
			ORDER BY s.season_number, `index`;
		""", (series_id,))
		episode_info = list(map(dict, cursor))
		if not episode_info:
			return 'Series is empty'

	elif episode_number is None:
		# Get all episodes in a season of the series
		cursor.execute("""
			WITH season
			AS (
				SELECT
					id,
					`index` AS season_number
				FROM metadata_items
				WHERE
					metadata_type = 3
					AND parent_id = ?
					AND `index` = ?
				)
			SELECT
				title,
				season_number,
				`index` AS episode_number,
				mi.id
			FROM metadata_items mi
			INNER JOIN season s
			ON mi.parent_id = s.id
			WHERE metadata_type = 4
			ORDER BY `index`;
		""", (series_id, season_number))
		episode_info = list(map(dict, cursor))
		if not episode_info:
			return 'Season not found'

	else:
		# Get a specific episode of the series
		cursor.execute("""
			WITH season
			AS (
				SELECT
					id,
					`index` AS season_number
				FROM metadata_items
				WHERE
					metadata_type = 3
					AND parent_id = ?
					AND `index` = ?
				)
			SELECT
				title,
				season_number,
				`index` AS episode_number,
				mi.id
			FROM metadata_items mi
			INNER JOIN season s
			ON mi.parent_id = s.id
			WHERE
				metadata_type = 4
				AND `index` = ?;
		""", (series_id, season_number, episode_number))
		episode_info = list(map(dict, cursor))
		if not episode_info:
			return 'Episode not found'
	return episode_info

def _add_intro(row_cursor, cursor, episode_info: List[dict], intro_begin: int, intro_end: int) -> Union[str, None]:
	# Convert timestamps given to ms
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

	intro_inserts = []
	for episode in episode_info:
		# Check for existing intros
		result = row_cursor.execute("""
			SELECT tag_id, `index`
			FROM taggings
			WHERE text = 'intro'
				AND metadata_item_id = ?
			ORDER BY `index` DESC
			LIMIT 1;
			""", 
			(episode['id'],)
		).fetchone()
		d = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		if result is None:
			# Episode doesn't have intro yet
			cursor.execute("""
				SELECT
					(
						SELECT tag_id AS main
						FROM taggings
						WHERE text = 'intro'
					),
					(
						SELECT tag_id + 1 AS alt
						FROM taggings
						ORDER BY tag_id DESC
						LIMIT 1
					);
				""")
			i = cursor.fetchone()
			result = [i[0] or i[1], 0]
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
	return

def _shift_intro(cursor, episode_info: List[dict], intro_offset: int) -> None:
	for episode in episode_info:
		cursor.execute("""
			UPDATE taggings
			SET
				time_offset = time_offset + (? * 1000),
				end_time_offset = end_time_offset + (? * 1000)
			WHERE text = 'intro'
				AND metadata_item_id = ?;
			""",
			(intro_offset, intro_offset, episode['id'],)
		)
	return

def _edit_intro(cursor, intro_number: int, intro_begin: str, intro_end: str) -> Union[str, None]:
	# Convert timestamps given to ms
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

	cursor.execute(
		"UPDATE taggings SET time_offset = ?, end_time_offset = ? WHERE id = ?",
		(intro_begin, intro_end, intro_number)
	)
	return

def _remove_intro(cursor, intro_number) -> None:
	cursor.execute("DELETE FROM taggings WHERE id = ?", (intro_number,))
	return

def intro_marker_editor(
	action: str,
	library_name: str, series_name: str, season_number: int=None, episode_number: int=None,
	intro_number: int=None, intro_begin: str=None, intro_end: str=None, intro_offset: int=None
) -> List[int]:
	result_json = []

	# Check for illegal arg parsing
	if not isdir(plex_data_directory):
		return 'The plex data directory could not be found'
	db_location = join(plex_data_directory, 'Plug-in Support', 'Databases', 'com.plexapp.plugins.library.db')
	if not isfile(db_location):
		return 'The plex database file could not be found'
	if not action in actions:
		return 'Unknown action'
	if action == 'add' and not (intro_begin and intro_end):
		return 'Add requires a value for intro_begin and intro_end'
	if action == 'remove' and not intro_number:
		return 'Remove requires a value for intro_number'
	if action == 'edit' and not (intro_number and intro_begin and intro_end):
		return 'Edit requires a value for intro_number, intro_begin and intro_end'
	if action == 'shift' and not intro_offset:
		return 'Shift requires a value for intro_offset'
	if episode_number is not None and season_number is None:
		return '"season_number" has to be set when "episode_number" is set'

	# Create connection to plex database
	db = connect(db_location, timeout=20.0)
	row_cursor = db.cursor()
	db.row_factory = Row
	cursor = db.cursor()

	if action in ('edit','remove') and intro_number:
		cursor.execute("SELECT 1 FROM taggings WHERE id = ? LIMIT 1", (intro_number,))
		if cursor.fetchone() is None:
			return 'Intro number not found'

	# Get library id and series id
	row_cursor.execute("""
		SELECT id
		FROM library_sections
		WHERE
			name = ?
			AND section_type = 2
		LIMIT 1;
		""",
		(library_name,)
	)
	lib_id = next(iter(row_cursor.fetchone()), None)
	if lib_id is None:
		return 'Library not found or not a show library'

	row_cursor.execute("""
		SELECT id
		FROM metadata_items
		WHERE 
			library_section_id = ?
			AND title = ?
		""",
		(lib_id, series_name)
	)
	series_id = next(iter(row_cursor.fetchone()), None)
	if series_id is None:
		return 'Series not found'

	# Get targeted episodes
	episode_info = _get_episodes(cursor, series_id, season_number, episode_number)
	if isinstance(episode_info, str):
		return episode_info

	# Do what is requested
	if action == 'add':
		result = _add_intro(row_cursor, cursor, episode_info, intro_begin, intro_end)
		if result:
			return result

	elif action == 'shift':
		_shift_intro(cursor, episode_info, intro_offset)

	elif action == 'edit':
		result = _edit_intro(cursor, intro_number, intro_begin, intro_end)
		if result:
			return result

	elif action == 'remove':
		_remove_intro(cursor, intro_number)

	db.commit()

	# Find the intro markers for each episode
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
			ORDER BY `index`;
		""", (episode['id'],))
		media_to_intro[episode['id']] = list(map(dict, cursor))
	for episode in episode_info:
		episode.update({'intros': media_to_intro.get(episode['id'], [])})
		result_json.append(episode.pop('id'))

	print(dumps(episode_info, indent=4))

	return result_json

if __name__ == '__main__':
	from argparse import ArgumentParser

	# Setup arg parsing
	parser = ArgumentParser(description='Edit the intro markers of plex media')
	parser.add_argument('-l','--LibraryName', type=str, help='Name of the series library to target', required=True)
	parser.add_argument('-s','--SeriesName', type=str, help='Name of the series in the target library to target', required=True)
	parser.add_argument('-S','--SeasonNumber', type=int, help='Target a specific season inside the targeted series based on it\'s number (only accepted when -s is given) (specials is 0)')
	parser.add_argument('-e','--EpisodeNumber', type=int, help='Target a specific episode inside the targeted season based on it\'s number (only accepted when -S is given)')

	parser.add_argument('-a','--Action', help='The type of action you want to perform on the intro marker of the media', choices=actions, required=True)
	parser.add_argument('-n','--IntroNumber', type=int, help='REMOVE/EDIT ONLY: The number of the intro marker, shown when using -a list')
	parser.add_argument('-B','--IntroBegin', type=str, help='ADD/EDIT ONLY: The start of the intro marker. Supported formats are miliseconds and MM:SS')
	parser.add_argument('-E','--IntroEnd', type=str, help='ADD/EDIT ONLY: The end of the intro marker. Supported formats are miliseconds and MM:SS')
	parser.add_argument('-O','--IntroOffset', type=int, help='SHIFT ONLY: The amount to shift the intro marker(s) in seconds (negative values supported)')

	args = parser.parse_args()
	# Call function and process result
	response = intro_marker_editor(
		action=args.Action,
		library_name=args.LibraryName, series_name=args.SeriesName, season_number=args.SeasonNumber, episode_number=args.EpisodeNumber,
		intro_number=args.IntroNumber, intro_begin=args.IntroBegin, intro_end=args.IntroEnd, intro_offset=args.IntroOffset
	)
	if not isinstance(response, list):
		parser.error(response)
