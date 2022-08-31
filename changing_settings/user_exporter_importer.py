#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Export plex user data to a database file that can then be read from to import the data back (on a different plex instance or for a different user)
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

from os import getenv, path
from sqlite3 import connect, OperationalError

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = f"http://{plex_ip}:{plex_port}"

process_summary = {
	'watched_status': "The watched status of the media for the user: watched, not watched or partially watched.",
	'playlist': "The playlists of the user"
}
#guid -> ratingkey
#lib_id -> lib_output
#'sections' -> sections output
guid_map = {}

def _guid_to_ratingkey(ssn, guid: str):
	global guid_map

	rating_key = guid_map.get(guid)
	if rating_key == None:
		if not 'sections' in guid_map:
			guid_map['sections'] = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory',[])

		for lib in guid_map['sections']:
			if lib['type'] == 'movie':
				media_type = '1'
			elif lib['type'] == 'show':
				media_type = '4'
			else: continue
			if not lib['key'] in guid_map:
				guid_map[lib['key']] = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'type': media_type, 'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])

			for media in guid_map[lib['key']]:
				media_guid = str(media['Guid'])
				if media_guid == guid:
					rating_key = media['ratingKey']
					guid_map[media_guid] = media['ratingKey']
					break
			else:
				continue
			break
		else:
			rating_key = None

	return rating_key

def _watched_process(ssn, cursor, type: str, name: str, user_token: str):
	ssn.params.update({'X-Plex-Token': user_token})
	if type == 'export':
		cursor.execute(f"""
			CREATE TABLE IF NOT EXISTS `{name}-watched`(
				guid VARCHAR(255) PRIMARY KEY,
				watched_status INTEGER
			);
		""")
		sections = ssn.get(f'{base_url}/library/sections').json()['MediaContainer'].get('Directory',[])
		for lib in sections:
			if lib['type'] == 'movie':
				media_type = '1'
			elif lib['type'] == 'show':
				media_type = '4'
			else: continue
			lib_output = ssn.get(f'{base_url}/library/sections/{lib["key"]}/all', params={'type': media_type,'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])
			#watched status: -1 = watched, -2 = not watched, >=0 = view offset (partially watched)
			entries = {str(m['Guid']): m.get('viewOffset', -1 if 'viewCount' in m else -2) for m in lib_output if 'Guid' in m}
			cursor.executemany(f"INSERT OR IGNORE INTO `{name}-watched`(guid) VALUES (?);", ((e,) for e in entries.keys()))
			cursor.executemany(f"UPDATE `{name}-watched` SET watched_status = ? WHERE guid = ?", zip(entries.values(), entries.keys()))

	elif type == 'import':
		try:
			cursor.execute(f"SELECT * FROM `{name}-watched`")
		except OperationalError:
			return
		media_entries = cursor.fetchall()
		for media in media_entries:
			rating_key = _guid_to_ratingkey(ssn, media[0])
			if rating_key == None:
				continue

			if media[1] == -1:
				ssn.get(f'{base_url}/:/scrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key})
			elif media[1] == -2:
				ssn.get(f'{base_url}/:/unscrobble', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key})
			else:
				ssn.get(f'{base_url}/:/progress', params={'identifier': 'com.plexapp.plugins.library', 'key': rating_key, 'time': media[1], 'state': 'stopped'})

	return

def _playlist_process(ssn, cursor, type: str, name: str, user_token: str):
	ssn.params.update({'X-Plex-Token': user_token})
	if type == 'export':
		cursor.execute(f"""
			CREATE TABLE IF NOT EXISTS `{name}-playlist`(
				guid VARCHAR(255) PRIMARY KEY,
				title VARCHAR(255),
				summary TEXT,
				playlistType VARCHAR(20),
				content TEXT,
				thumb BLOB,
				art BLOB
			);
		""")
		playlists = ssn.get(f'{base_url}/playlists').json()['MediaContainer'].get('Metadata',[])
		insert_playlists = []
		for playlist in playlists:
			playlist_content = ssn.get(f'{base_url}{playlist["key"]}', params={'includeGuids': '1'}).json()['MediaContainer'].get('Metadata',[])
			playlist_guids = "|".join(str(e['Guid']) for e in playlist_content if 'Guid' in e)
			insert_playlists.append((playlist['title'], playlist['summary'], playlist['playlistType'], playlist_guids, playlist.get('thumb',None), playlist.get('art',None), playlist['guid']))
		cursor.executemany(f"INSERT OR IGNORE INTO `{name}-playlist`(guid) VALUES (?);", (e[::-1][0:1] for e in insert_playlists))
		cursor.executemany(f"UPDATE `{name}-playlist` SET title = ?, summary = ?, playlistType = ?, content = ?, thumb = ?, art = ? WHERE guid = ?", insert_playlists)

	elif type == 'import':
		try:
			cursor.execute(f"SELECT * FROM `{name}-playlist`")
		except OperationalError:
			return
		playlist_entries = cursor.fetchall()
		machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
		for playlist in playlist_entries:
			#create playlist
			rating_keys = ",".join(filter(lambda x: x != None, (_guid_to_ratingkey(ssn, g) for g in playlist[4].split("|"))))
			new_ratingkey = ssn.post(f'{base_url}/playlists', params={'type': playlist[3], 'title': playlist[1], 'smart': '0', 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{rating_keys}'}).json()['MediaContainer']['Metadata'][0]['ratingKey']
			#set summary
			if playlist[2] or '' != '':
				ssn.put(f'{base_url}/playlists/{new_ratingkey}', params={'summary': playlist[2]})
			#set images
			if playlist[5] or '' != '':
				ssn.post(f'{base_url}/playlists/{new_ratingkey}/posters', data=playlist[5])
			if playlist[6] or '' != '':
				ssn.post(f'{base_url}/playlists/{new_ratingkey}/arts', data=playlist[6])

	return

def _leave(cursor, e=None):
	#called upon early exit of script
	print('Shutting down...')
	cursor.connection.commit()
	print('Progress saved')
	if e != None:
		print('AN ERROR OCCURED. ALL YOUR PROGRESS IS SAVED. PLEASE SHARE THE FOLLOWING WITH THE DEVELOPER:')
		raise e
	exit(0)

def user_exporter_importer(ssn, type: str, user: str, name: str, process: list, location: str):
	#check for illegal arg parsing
	if not type in ('export','import','list'):
		return 'Invalid type'
	if type in ('export','import'):
		if user == None:
			return 'User not given'
		if name == None:
			return 'Name not given'
		if process == None:
			return 'Process not given'
	if not name.isalnum():
		return 'Invalid name; name needs to consist of alpha numeric characters (letters and numbers)'

	#setup db location
	if type in ('export','list'):
		if path.isdir(location):
			database_file = f'{path.splitext(path.abspath(__file__))[0]}.db'
			if path.isfile(database_file):
				print(f'Exporting to {database_file} (Updating)')
			else:
				print(f'Exporting to {database_file}')

		elif location.endswith('.db'):
			database_file = location
			if path.isfile(location):
				print(f'Exporting to {database_file} (Updating)')
			else:
				print(f'Exporting to {database_file}')

		else:
			return 'Location not found'

	elif type == 'import':
		if path.isfile(location):
			database_file = location
			print(f'Importing from {database_file}')
		else:
			return 'Location not found'

	#get user data
	machine_id = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	shared_users = ssn.get(f'http://plex.tv/api/servers/{machine_id}/shared_servers').text
	result = map(lambda r: r.split('"')[0:7:6], shared_users.split('username="')[1:])
	user_data = dict(result)
	#get own username
	own_username = ssn.get('http://plex.tv/api/v2/user').json()['username']
	user_data[own_username] = plex_api_token

	#setup db connection and db
	cursor = connect(database_file).cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS users(name VARCHAR(255) PRIMARY KEY);")
	if type == 'list':
		cursor.execute("SELECT name FROM users;")
		result_json = [i[0] for i in cursor.fetchall()]
		print('Names in database: ' + str(result_json))
		print('Usernames on server: ' + str(list(user_data.keys())))
		return result_json

	#check if user exists
	if not user in user_data:
		return 'User not found'
	else:
		user_token = user_data[user]

	#check name
	cursor.execute("SELECT name FROM users WHERE name = ?", (name,))
	if cursor.fetchone() == None:
		if type == 'import':
			return 'Name not found in database'
		elif type == 'export':
			cursor.execute("INSERT INTO users VALUES (?)", (name,))

	try:
		#start processing
		if 'watched_status' in process:
			_watched_process(ssn, cursor, type, name, user_token)

		if 'playlist' in process:
			_playlist_process(ssn, cursor, type, name, user_token)

	except Exception as e:
		if 'has no column named' in str(e):
			_leave(cursor, e='Database file is too old, please delete the file and export to a new one')
		else:
			_leave(cursor, e=e)
	else:
		cursor.connection.commit()

	return

if __name__ == '__main__':
	from requests import Session
	from argparse import ArgumentParser, RawDescriptionHelpFormatter

	#setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#setup arg parsing
	epilog = """-------------------
EPILOG

-p/--Process
{p}

-L/--Location
	When using the script, you might want to influence how the script handles the database file,
	which you can set using the -L/--Location option. See:

	When exporting and not giving this argument, the database file will be put in the same folder as the script.
	When exporting and giving a path to a folder, the database file will be put in that folder.
	When exporting and giving a path to a database file, that database file will be used to put the data in or will be updated if data is already in it (STRONGLY RECOMMENDED IF POSSIBLE)
	When importing and giving a path to a database file, that database file will be read and used as the source of the data that will be applied
""".format(p="\n".join(map(lambda k: f'	{k[0]}: {k[1]}', process_summary.items())))
	parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter, description='Export plex user data to a database file that can then be read from to import the data back (on a different plex instance or for a different user)', epilog=epilog)
	parser.add_argument('-t','--Type', choices=['export','import','list'], help='Export/import user data or list stored users in database and users on the server', required=True)
	parser.add_argument('-u','--User', type=str, help='EXPORT/IMPORT ONLY: Username of user to target')
	parser.add_argument('-n','--Name', type=str, help='EXPORT/IMPORT ONLY: Name that data will be/is stored under in database')
	parser.add_argument('-p','--Process', choices=process_summary.keys(), help='EXPORT/IMPORT ONLY: Select what to export/import; this argument can be given multiple times to select multiple things', action='append', default=None)
	parser.add_argument('-L','--Location', type=str, help='SEE EPILOG', default=path.dirname(path.abspath(__file__)))

	args = parser.parse_args()
	#call function and process result
	response = user_exporter_importer(ssn=ssn, type=args.Type, user=args.User, name=args.Name, process=args.Process, location=args.Location)
	if isinstance(response, str):
		parser.error(response)
