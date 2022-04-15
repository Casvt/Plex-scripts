#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
        When a stream starts, find the movie script when possible and put it in a file in the movie folder
Requirements (python3 -m pip install [requirement]):
        requests
Setup:
        In Tautulli, go to Settings -> Notification Agents -> Add a new notification agent -> Script
        Configuration:
                Script Folder = folder where this script is stored
                Script File = select this script
                Script Timeout = 30
                Description is optional
        Triggers:
                Playback Start = check
        Conditions:
                Media Type is movie
        Arguments:
                Playback Start -> Script Arguments = --Title {title} --File {file}
        SAVE
"""

import requests, argparse, os, re

def find_script(title):
        output = requests.post('https://imsdb.com/search.php', {'search_query': title, 'submit':'Go%21'}, headers={'X-HTTP-Method-Override': 'GET'}).text
        web_link = re.findall('(?i)(?:(?<=href=")/Movie Scripts/.*?\.html(?=" title="[^"]+">' + title + '))', output)
        if len(web_link) == 0: return None
        else: web_link = web_link[0]
        output = requests.get('https://imsdb.com' + web_link).text
        script_link = re.findall('(?i)(/scripts/.*?\.html)', output)
        if len(script_link) == 0: return None
        else: script_link = script_link[0]
        output = requests.get('https://imsdb.com' + script_link).text
        script = re.findall('<pre>.*</pre>', output, re.DOTALL)
        if len(script) == 0: return None
        else: script = script[0].replace('</pre>', '').replace('<pre>', '').replace('</b>', '').replace('<b>', '')
        return script

parser = argparse.ArgumentParser(description="When a stream starts, find the movie script when possible and put in in a file in the movie folder")
parser.add_argument('-t','--Title', help="Title of the media", required=True)
parser.add_argument('-f','--File', help="Filepath to media file", required=True)
args = parser.parse_args()
if not os.path.isfile(args.File):
        parser.error('Media file does not exist')
dest = os.path.splitext(args.File)[0] + '_script.txt'
if os.path.isfile(dest): exit(0)
else:
        script = find_script(args.Title)
        if script != None:
                with open(dest, 'w') as f:
                        f.write(script)
