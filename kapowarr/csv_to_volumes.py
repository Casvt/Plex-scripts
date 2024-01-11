#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	From a CSV file where the first column is the CV ID's of volumes, add them all.
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below, then run the script.
"""

kapowarr_base_url = '' # e.g. 'http://192.168.2.15:5656'
kapowarr_api_token = '' # Settings -> General -> Security

csv_filepath = '' # e.g. /home/user/volumes.csv
root_folder = '' # e.g. /mnt/media/comics
monitored = True # True or False

from os.path import isfile, sep

def csv_to_volumes(
	ssn,
	csv_file: str,
	root_folder: str,
	monitored: bool
) -> None:
	base_url = kapowarr_base_url.rstrip('/')
	rf_path = root_folder.rstrip(sep) + sep

	root_folders = ssn.get(f'{base_url}/api/rootfolder').json()['result']
	for rf in root_folders:
		if rf['folder'] == rf_path:
			rf_id = rf['id']
			break
	else:
		print('Root folder not found')
		return

	if not isfile(csv_file):
		print('CSV file not found')
		return

	with open(csv_filepath) as f:
		for volume in f:
			cv_id, title = volume.strip().split(',')
			if not cv_id.isdigit():
				continue
			ssn.post(f'{base_url}/api/volumes', json={
				'comicvine_id': cv_id,
				'root_folder_id': rf_id,
				'monitor': monitored
			})
			print(f'Added {title}')
	return

if __name__ == '__main__':
	from requests import Session

	# Setup vars
	ssn = Session()
	ssn.params.update({'api_key': kapowarr_api_token})

	csv_to_volumes(
		ssn,
		csv_filepath,
		root_folder,
		monitored
	)
