#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Set the "Limit remote stream bitrate" setting based on the amount of streams
Requirements (python3 -m pip install [requirement]):
	requests
Setup:
	Fill the variables below firstly, then run the script with -h to see the arguments that you need to give.
	Run this script at an interval. Decide for yourself what the interval is (e.g. every 20m or every 12h)
"""

plex_ip = ''
plex_port = ''
plex_api_token = ''

bitrates = {
	#key is bitrate in kbps; value is the amount of streams that at least need to be active for that value to be set
	'320': 20, #20+ streams
	'720': 14, #14-19 streams
	'1500': 13,
	'2000': 12,
	'3000': 11,
	'4000': 10,
	'8000': 9,
	'10000': 8,
	'12000': 7,
	'15000': 6,
	'20000': 5,
	'25000': 4,
	'30000': 3,
	'40000': 2,
	# 0 is "Original (no limit)"
	'0': 0 #0-1 stream
}

from os import getenv

# Environmental Variables
plex_ip = getenv('plex_ip', plex_ip)
plex_port = getenv('plex_port', plex_port)
plex_api_token = getenv('plex_api_token', plex_api_token)
bitrates = getenv('bitrates', bitrates)
base_url = f"http://{plex_ip}:{plex_port}"

def limit_remote_stream_bitrate(ssn):
	sessions = ssn.get(f'{base_url}/status/sessions').json()['MediaContainer'].get('Metadata',[])
	if len(sessions) >= 0:
		session_count = len(sessions)
		if session_count >= bitrates['320']:
			ssn.put(f'{base_url}/:/prefs', params={'WanPerStreamMaxUploadRate': '320'})
			result_json = ['320']
		else:
			for bitrate, stream_count in reversed(bitrates.items()):
				if session_count < stream_count:
					bitrate_index = list(bitrates.keys()).index(bitrate)
					if not bitrate_index + 1 == len(bitrates.keys()):
						bitrate = list(bitrates.keys())[bitrate_index + 1]
					ssn.put(f'{base_url}/:/prefs', params={'WanPerStreamMaxUploadRate': bitrate})
					result_json = [bitrate]
					break

				elif stream_count == session_count:
					ssn.put(f'{base_url}/:/prefs', params={'WanPerStreamMaxUploadRate': bitrate})
					result_json = [bitrate]
					break

	return result_json

if __name__ == '__main__':
	from requests import Session

	#setup vars
	ssn = Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': plex_api_token})

	#call function and process result
	response = limit_remote_stream_bitrate(ssn=ssn)
	if not isinstance(response, list):
		print(response)
