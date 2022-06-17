#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Remove all artwork, poster and theme files that aren't used by plex from the plex metadata folder
Requirements (python3 -m pip install [requirement]):
	NO REQUIREMENTS
Setup:
	Fill the variables below firstly, then run the script
	You can find out what the location of you plex data directory is here: https://support.plex.tv/articles/202915258-where-is-the-plex-media-server-data-directory-located/
"""

plex_data_dir = '/var/lib/plexmediaserver/Library/Application Support/Plex Media Server'

import os
from shutil import rmtree

# Environmental Variables
plex_data_dir = os.getenv('plex_data_dir', plex_data_dir)

def remove_unused_artwork(plex_data_dir: str):
	result_json = []

	#check if script is run as root
	if os.getegid() != 0:
		return 'Error: script not run as root'

	#check if data dir exists
	if not os.path.isdir(plex_data_dir):
		return 'Error: data directory doesn\'t exist or cannot be accessed'

	os.chdir(os.path.join(plex_data_dir,'Metadata'))
	for dir in os.listdir():
		if not dir in ('Albums','Movies','TV Shows','Artists'): continue
		for sub_dir in os.listdir(dir):
			for bundle in os.listdir(os.path.join(dir, sub_dir)):
				for bundle_folder in os.listdir(os.path.join(dir, sub_dir, bundle)):
					if not bundle_folder == 'Contents':
						rmtree(os.path.join(dir, sub_dir, bundle, bundle_folder))
						print(os.path.join(dir, sub_dir, bundle, bundle_folder))
						result_json.append(os.path.join(dir, sub_dir, bundle, bundle_folder))
						continue

					for sub_bundle_folder in os.listdir(os.path.join(dir, sub_dir, bundle, bundle_folder)):
						if not sub_bundle_folder in ('_stored','_combined'):
							rmtree(os.path.join(dir, sub_dir, bundle, bundle_folder, sub_bundle_folder))
							print(os.path.join(dir, sub_dir, bundle, bundle_folder, sub_bundle_folder))
							result_json.append(os.path.join(dir, sub_dir, bundle, bundle_folder, sub_bundle_folder))

	return result_json

if __name__ == '__main__':
	#call function and process result
	response = remove_unused_artwork(plex_data_dir=plex_data_dir)
	if not isinstance(response, list):
		print(response)
