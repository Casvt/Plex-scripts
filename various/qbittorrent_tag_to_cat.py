#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	If a torrent has a certain tag, then apply certain categories
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly,
	then go to the qbittorrent web-ui -> Options -> Downloads -> Run external program on torrent completion:
		/usr/bin/python3 /path/to/qbittorrent_tag_to_cat.py -t [TAGNAME] -c [CAT1] -c [CAT2 (optional)]
"""

qbittorrent_ip = ''
qbittorrent_port = ''
qbittorrent_username = ''
qbittorrent_password = ''

from os import getenv

# Environmental Variables
qbittorrent_ip = getenv('qbittorrent_ip', qbittorrent_ip)
qbittorrent_port = getenv('qbittorrent_port', qbittorrent_port)
qbittorrent_username = getenv('qbittorrent_username', qbittorrent_username)
qbittorrent_password = getenv('qbittorrent_password', qbittorrent_password)
base_url = f"http://{qbittorrent_ip}:{qbittorrent_port}/api/v2"

def qbittorrent_tag_to_cat(ssn, tag_name: str, categories: list, wait: int=0):
	result_json = []

	if wait > 0:
		from time import sleep
		sleep(wait)

	#authenticate
	ssn.get(f'{base_url}/auth/login', params={'username': qbittorrent_username, 'password': qbittorrent_password})

	#get torrents
	torrents = ssn.get(f'{base_url}/torrents/info').json()
	for torrent in torrents:
		if tag_name in torrent.get('tags','').split(', '):
			#tag found on torrent
			for cat in categories:
				ssn.post(f'{base_url}/torrents/setCategory', params={'hashes': torrent['hash'], 'category': cat})

			result_json.append(torrent['hash'])

	return result_json

if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()

	#setup arg parsing
	parser = argparse.ArgumentParser(description='If a torrent has a certain tag, then apply certain categories')
	parser.add_argument('-t','--TagName', type=str, help="The name of the tag to apply the categories to", required=True)
	parser.add_argument('-c','--CategoryName', type=str, help="The name of the category to apply to the torrent; give this argument multiple times to apply multiple categories", action='append', required=True)
	parser.add_argument('-w','--Wait', type=int, help="Wait X seconds before running the script on the torrents", default=0)

	args = parser.parse_args()
	#call function and process result
	response = qbittorrent_tag_to_cat(ssn=ssn, tag_name=args.TagName, categories=args.CategoryName, wait=args.Wait)
	if not isinstance(response, list):
		parser.error(response)
