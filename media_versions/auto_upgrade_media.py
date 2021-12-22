#!/usr/bin/python3

#The use case of this script is the following:
#	Check every library in the list below and if an episode/movie is viewed alot, upgrade it
#	and if it hasn't been viewed much, downgrade it; using sonarr and radarr
#	Radarr: script will change quality profile of movie and initiate search for it
#	Sonarr: script will change quality profile of series, initiate search for episodes and change quality profile of series back

plex_ip = ''
plex_port = ''
plex_api_token = ''

#atleast one is required; both is possible ofcourse if you want to up/downgrade both movies and episodes
radarr_ip = ''
radarr_port = ''
radarr_api_token = ''
#name of profile to apply to movie for every resolution (if you do not provide a name for a resolution, the script will not up/downgrade to that resolution)
radarr_profile_480 = ''
radarr_profile_720 = ''
radarr_profile_1080 = ''
radarr_profile_4k = ''

sonarr_ip = ''
sonarr_port = ''
sonarr_api_token = ''
#name of profile to apply to series for every resolution (series profile is changed, episodes are searched and profile will be changed back) (if you do not provide a name for a resolution, the script will not up/downgrade to that resolution)
sonarr_profile_480 = ''
sonarr_profile_720 = ''
sonarr_profile_1080 = ''
sonarr_profile_4k = ''

import requests
import time
import re
import getopt
import sys

if not (radarr_ip or radarr_port or radarr_api_token or sonarr_ip or sonarr_port or sonarr_api_token):
	print("Error: must add atleast one *arr")
	exit(1)
if not re.search('^(\d{1,3}\.){3}\d{1,3}$', plex_ip):
	print("Error: " + plex_ip + " is not a valid ip")
	exit(1)
if not re.search('^\d{1,5}$', plex_port):
	print("Error: " + plex_port + " is not a valid port")
	exit(1)
if not re.search('^[\w\d_-~]{19,21}$', plex_api_token):
	print("Error: " + plex_api_token + " is not a valid api token")
	exit(1)
if sonarr_ip or sonarr_port or sonarr_api_token:
	if not re.search('^(\d{1,3}\.){3}\d{1,3}$', sonarr_ip):
		print("Error: " + sonarr_ip + " is not a valid ip")
		exit(1)
	if not re.search('^\d{1,5}$', sonarr_port):
		print("Error: " + sonarr_port + " is not a valid port")
		exit(1)
	if not re.search('^[a-z0-9]{30,36}$', sonarr_api_token):
		print("Error: " + sonarr_api_token + " is not a valid api token")
		exit(1)
if radarr_ip or radarr_port or radarr_api_token:
	if not re.search('^(\d{1,3}\.){3}\d{1,3}$', radarr_ip):
		print("Error: " + radarr_ip + " is not a valid ip")
		exit(1)
	if not re.search('^\d{1,5}$', radarr_port):
		print("Error: " + radarr_port + " is not a valid port")
		exit(1)
	if not re.search('^[a-z0-9]{30,36}$', radarr_api_token):
		print("Error: " + radarr_api_token + " is not a valid api token")
		exit(1)

baseurl = 'http://' + plex_ip + ':' + plex_port
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})

res_ladder = {}
res_ladder['480'] = {"Downgrade": False, "Upgrade": {"movie": radarr_profile_720, "episode": sonarr_profile_720}}
res_ladder['720'] = {"Downgrade": {"movie": radarr_profile_480, "episode": sonarr_profile_480}, "Upgrade": {"movie": radarr_profile_1080, "episode": sonarr_profile_1080}}
res_ladder['1080'] = {"Downgrade": {"movie": radarr_profile_720, "episode": sonarr_profile_720}, "Upgrade": {"movie": radarr_profile_4k, "episode": sonarr_profile_4k}}
res_ladder['4k'] = {"Downgrade": {"movie": radarr_profile_1080, "episode": sonarr_profile_1080}, "Upgrade": False}

def help():
	print('	-h/--Help')
	print('		Display this help message')
	print('Required:')
	print('	-l/--LibraryName [name of target library (movie or show library)')
	print('		Pass this argument multiple times to apply the script to multiple libraries; movie and show libraries are allowed to be mixed')
	print('At least one required:')
	print('	-d/--DowngradeDays [number]')
	print('		The amount of days that the media has not been watched before downgrading one resolution (4k -> 1080p -> 720p)')
	print('	-D/--DowngradeViewCount [number]')
	print('		The viewcount which the video should be below or equal to to downgrade it (4k -> 1080p -> 720p)')
	print('	-u/--UpgradeDays [number]')
	print('		The amount of days which the last watch date should fall within to upgrade (e.g. 7 = if the movie has been watched within the last 7 days, upgrade it) (720p -> 1080p -> 4k)')
	print('	-U/--UpgradeViewCount [number]')
	print('		The viewcount which the video should be above to upgrade it (720p -> 1080p -> 4k)')

def updown(media_info, queue, UpOrDown='down', last=False):
	if not queue: queue = {}
	if last == True:
		#process queue
		first_key = ''
		for key in queue.keys():
			first_key = key
			break
		if not first_key: return queue
		if 'series_id' in queue[str(first_key)].keys():
			#queue is a sonarr queue; {'series_id_1': {'profile_id_1': ['episode_id_1', 'episode_id_2'], 'profile_id_2': ['episode_id_3', 'episode_id_4']}}
			series_profileid_history = {}
			for key in queue.keys():
				#do this for every series
				series_output = requests.get('http://' + str(sonarr_ip) + ':' + str(sonarr_port) + '/api/v3/series/' + str(key), params={'apikey': sonarr_api_token}).json()
				series_profileid_history[str(key)] = series_output['qualityProfileId']
				for profile in queue[key].keys():
					#do this for every profile that an episode in the series needs to be searched with
					series_output['qualityProfileId'] = profile
					requests.put('http://' + str(sonarr_ip) + ':' + str(sonarr_port) + '/api/v3/series/' + str(key), json=series_output, params={'apikey': sonarr_api_token})
					requests.post('http://' + str(sonarr_ip) + ':' + str(sonarr_port) + '/api/v3/command', json={'name': 'EpisodeSearch', 'episodeIds': queue[key][profile]})
				#every episode of the series that needed to be up/downgraded has been searched so change profile of series back to what is was
				series_output['qualityProfileId'] = series_profileid_history[str(key)]
				requests.put('http://' + str(sonarr_ip) + ':' + str(sonarr_port) + '/api/v3/series/' + str(key), json=series_output, params={'apikey': sonarr_api_token})
		else:
			#queue is a radarr queue; {'profile_id_1': ['movie_id_1', 'movie_id_2'], 'profile_id_2': ['movie_id_3', 'movie_id_4']}
			research_queue = []
			for key in queue.keys():
				#do this for every profile that movies need to be up/downgraded to
				requests.put('http://' + radarr_ip + ':' + radarr_port + '/api/v3/movie/editor', json={'movieIds': queue[key], 'qualityProfileId': int(key)}, params={'apikey': radarr_api_token})
				for item in queue[key]:
					#add every movie's id to a list to initiate a search for
					research_queue.append(item)
			#initiate a search for every movie that has changed in quality profile
			requests.post('http://' + radarr_ip + ':' + radarr_port + '/api/v3/command', json={'movieIds': research_queue, 'name': "MoviesSearch"}, params={'apikey': radarr_api_token})
		return queue
	movie_id = ''
	profile_id = ''
	#get the name of the new quality profile for the media
	if UpOrDown == 'down': profile_name = res_ladder[str(media_info['Media'][0]['videoResolution'])]['Downgrade'][media_info['type']]
	elif UpOrDown == 'up': profile_name = res_ladder[str(media_info['Media'][0]['videoResolution'])]['Upgrade'][media_info['type']]
	if not profile_name: return queue
	filepath_current_file = media_info['Media'][0]['Part'][0]['file']
	if media_info['type'] == 'movie':
		#media is a movie
		#get the radarr id of the movie
		for movie in radarr_movies_output:
			if 'movieFile' in movie.keys() and movie['movieFile']['path'] == filepath_current_file:
				movie_id = movie['id']
				break
		if not movie_id: return queue
		#get the profile id for the new profile
		for profile in radarr_profiles_output:
			if profile['name'] == profile_name:
				profile_id = profile['id']
				break
		if not profile_id: return queue
		#add movie to the queue
		if not str(profile_id) in queue.keys(): queue[str(profile_id)] = []
		queue[str(profile_id)].append(int(movie_id))

	elif media_info['type'] == 'episode':
		#media is an episode
		#get sonarr info about episode and note series id and episode id
		episode_info = requests.get('http://' + sonarr_ip + ':' + sonarr_port + '/api/v3/parse', params={'apikey': sonarr_api_token, 'path': filepath_current_file}).json()['episodes'][0]
		series_id = episode_info['seriesId']
		episode_id = episode_info['id']
		if not series_id or not episode_id: return queue
		#get the profile id for the new profile
		for profile in sonarr_profile_output:
			if profile['name'] == profile_name:
				profile_id = profile['id']
				break
		if not profile_id: return queue
		#add episode to the queue
		if not str(series_id) in queue.keys(): queue[str(series_id)] = {}
		if not str(profile_id) in queue[str(series_id)].keys(): queue[str(series_id)][str(profile_id)] = []
		if not str(episode_id) in queue[str(series_id)][str(profile_id)]: queue[str(series_id)][str(profile_id)].append(int(episode_id))
	
	return queue


def updownCheck(media_info, media_indentation):
	#look at media and decide if media needs to be up/downgraded
	if downgrade_days and 'lastViewedAt' in media_info.keys() and media_info['lastViewedAt'] < time.time() - (86400 * downgrade_days):
		print(media_indentation + 'DOWNGRADING: Last time viewed was more than ' + str(downgrade_days) + ' days ago')
		return updown(media_info, edit_queue, 'down')

	elif downgrade_viewcount and 'viewCount' in media_info.keys() and media_info['viewCount'] <= downgrade_viewcount:
		print(media_indentation + 'DOWNGRADING: View count is lower or equal to ' + str(downgrade_viewcount))
		return updown(media_info, edit_queue, 'down')

	elif upgrade_days and 'lastViewedAt' in media_info.keys() and media_info['lastViewedAt'] > time.time() - (86400 * upgrade_days):
		print(media_indentation + 'UPGRADING: Last time viewed was within ' + str(upgrade_days) + ' days')
		return updown(media_info, edit_queue, 'up')

	elif upgrade_viewcount and 'viewCount' in media_info.keys() and media_info['viewCount'] > upgrade_viewcount:
		print(media_indentation + 'UPGRADING: View count is higher than ' + str(upgrade_viewcount))
		return updown(media_info, edit_queue, 'up')
	else: return edit_queue

section_output = ssn.get('http://' + plex_ip + ':' + plex_port + '/library/sections').json()
arguments, values = getopt.getopt(sys.argv[1:], 'hl:d:D:u:U:', ['Help', 'LibraryName=','DowngradeDays=','DowngradeViewcount=','UpgradeDays=','UpgradeViewcount='])
#don't give any value to these variables; run python3 auto_upgrade_media.py --Help
#process arguments gives and fill variables below with values of arguments
lib_ids = []
lib_types = {}
downgrade_days = ''
downgrade_viewcount = ''
upgrade_days = ''
upgrade_viewcount = ''
radarr_movies_output = ''
radarr_profiles_output = ''
sonarr_profile_output = ''
for argument, value in arguments:
	if argument in ('-h', '--Help'):
		help()
	if argument in ('-l', '--LibraryNames'):
		lib_found = False
		for level in section_output['MediaContainer']['Directory']:
			if level['title'] in value:
				if (level['type'] == 'movie' and radarr_ip) or (level['type'] == 'show' and sonarr_ip):
					lib_found = True
					lib_ids.append(level['key'])
					lib_types[level['key']] = level['type']
				else: print('Warning: library ' + str(value) + ' ignored as it isn\'t a movie/show library or the *arr for that type of lib isn\'t setup')
		if lib_found == False: print('Warning: library ' + str(value) + ' ignored as it isn\'t found')
	if argument in ('-d', '--DowngradeDays'):
		if re.search('^\d+$', value): downgrade_days = int(value)
		else:
			print('Error: invalid number given for ' + argument)
			exit(1)
	if argument in ('-D', '--DowngradeViewCount'):
		if re.search('^\d+$', value): downgrade_viewcount = int(value)
		else:
			print('Error: invalid number given for ' + argument)
			exit(1)
	if argument in ('-u', '--UpgradeDays'):
		if re.search('^\d+$', value): upgrade_days = int(value)
		else:
			print('Error: invalid number given for ' + argument)
			exit(1)
	if argument in ('-U', '--UpgradeViewCount'):
		if re.search('^\d+$', value): upgrade_viewcount = int(value)
		else:
			print('Error: invalid number given for ' + argument)
			exit(1)

if not lib_ids or not (downgrade_days or downgrade_viewcount or upgrade_days or upgrade_viewcount):
	print('Error: Arguments were not all given')
	help()
	exit(1)

for lib in lib_ids:
	#do this for every library
	edit_queue = {}
	lib_output = ssn.get(baseurl + '/library/sections/' + lib + '/all').json()
	if lib_types[lib] == 'movie':
		#lib is a movie lib
		if not radarr_movies_output: radarr_movies_output = requests.get('http://' + radarr_ip + ':' + radarr_port + '/api/v3/movie', params={'apikey': radarr_api_token}).json()
		if not radarr_profiles_output: radarr_profiles_output = requests.get('http://' + radarr_ip + ':' + radarr_port + '/api/v3/qualityprofile', params={'apikey': radarr_api_token}).json()
		for movie in lib_output['MediaContainer']['Metadata']:
			#do this for every movie in the lib
			print(movie['title'])
			edit_queue = updownCheck(movie, '	')

	elif lib_types[lib] == 'show':
		#lib is a show lib
		if not sonarr_profile_output: sonarr_profile_output = requests.get('http://' + sonarr_ip + ':' + sonarr_port + '/api/v3/qualityprofile', params={'apikey': sonarr_api_token}).json()
		for show in lib_output['MediaContainer']['Metadata']:
			#do this for every show in the lib
			print(show['title'])
			for episode in ssn.get(baseurl + '/library/metadata/' + show['ratingKey'] + '/allLeaves').json()['MediaContainer']['Metadata']:
				#do this for every episode of the show
				print('	' + show['title'] + ' - S' + str(episode['parentIndex']) + 'E' + str(episode['index']) + ' - ' + episode['title'])
				episode_output = ssn.get(baseurl + '/library/metadata/' + episode['ratingKey']).json()['MediaContainer']['Metadata'][0]
				edit_queue = updownCheck(episode_output, '		')

	#send off the queue that we made
	updown('GiraffesAreCool', edit_queue, last=True)
