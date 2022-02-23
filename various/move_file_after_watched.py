#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	After watching a movie, move the movie file from one folder to another.
IMPORTANT:
	When the file is directly in the source folder, the file + .srt, .ass and .nfo files with the same name will be moved
	When the file is in it's own sub-folder in the source folder, the complete folder that the file is in will be moved
	EXAMPLE:
		/mnt/plex-media/movies/cars/cars.mkv (movie file) + /mnt/plex-media/movies (source folder)
		->
		/mnt/plex-media-2/movies/cars/cars.mkv (/mnt/plex-media-2/movies = target folder)

		/mnt/plex-media/movies/cars.mkv (movie file) + /mnt/plex-media/movies (source folder)
		+ /mnt/plex-media/movies/cars.{srt,ass,nfo} (additional files)
		->
		/mnt/plex-media-2/movies/cars.mkv (/mnt/plex-media-2/movies = target folder)
		+ /mnt/plex-media-2/movies/cars.{srt,ass,nfo}
Requirements (python3 -m pip install [requirement]):
	PlexAPI
	websocket-client
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Once this script is run, it will keep running and will handle movie streams accordingly when needed.
	Run it in the background as a service or as a '@reboot' cronjob (cron only available on unix systems (linux and mac)).
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

import requests, time, os ,shutil, argparse, logging
from plexapi.server import PlexServer

baseurl = f'http://{plex_ip}:{plex_port}'
plex = PlexServer(baseurl, plex_api_token)
ssn = requests.Session()
ssn.headers.update({'Accept': 'application/json'})
ssn.params.update({'X-Plex-Token': plex_api_token})
logging_level = logging.INFO
logging.basicConfig(level=logging_level, format='[%(asctime)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S %d-%m-20%y')

parser = argparse.ArgumentParser(description="After watching a movie, the script will move the file to a different folder", epilog="See the top of the file for extra info about sub-folders")
parser.add_argument('-S','--SourceFolder', help="Folder from which movie files will be moved", required=True)
parser.add_argument('-T','--TargetFolder', help="Folder to which movie files will be moved", required=True)
args = parser.parse_args()
if not os.path.isdir(args.SourceFolder):
	parser.error('Source folder doesn\'t exist')
elif not args.SourceFolder.endsWith('/'):
	args.SourceFolder += '/'
if not os.path.isdir(args.TargetFolder):
	parser.error('Target folder doesn\'t exis')
elif not args.TargetFolder.endsWith('/'):
	args.TargetFolder += '/'
if args.SourceFolder == args.TargetFolder:
	parser.error('Source folder and target folder are not allowed to be the same')

def process(data):
	if not 'PlaySessionStateNotification' in data.keys(): return
	if data['PlaySessionStateNotification'][0]['state'] == 'stopped':
		media_output = ssn.get(f'{baseurl}/library/metadata/{data["PlaySessionStateNotification"][0]["ratingKey"]}').json()
		if media_output['MediaContainer']['Metadata'][0]['type'] == 'movie':
			if 'viewOffset' in media_output['MediaContainer']['Metadata'][0].keys() and not 'viewCount' in media_output['MediaContainer']['Metadata'][0].keys(): return
			for media in media_output['MediaContainer']['Metadata'][0]['Media']:
				for part in media['Part']:
					if os.path.basename(part['file']) == os.path.relpath(part['file'], args.SourceFolder):
						#move file with additional files (.srt, .ass and .nfo)
						for extension in ('.srt','.ass','.nfo', os.path.splitext(part['file'])[-1]):
							source = os.path.splitext(part['file'])[0] + extension
							target = os.path.join(args.TargetFolder, os.path.relpath(os.path.splitext(part['file'])[0] + extension, args.SourceFolder))
							shutil.move(source, target)
							logging.info(f'{source} moved to {target}')
					else:
						#move folder
						dest_folder = os.path.join(args.TargetFolder, os.path.relpath(os.path.dirname(part['file']), args.SourceFolder))
						os.makedirs(os.path.dirname(dest_folder), exist_ok=True)
						shutil.move(os.path.dirname(part['file']), dest_folder)
						logging.info(f'{os.path.dirname(part["file"])} moved to {dest_folder}')

if __name__  == '__main__':
	try:
		logging.info('Handling movie streams...')
		listener = plex.startAlertListener(callback=process)
		while True: time.sleep(5)
	except KeyboardInterrupt:
		logging.info('Shutting down')
		listener.stop()
