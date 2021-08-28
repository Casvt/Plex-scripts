#!/bin/bash

#The use case of this script is the following:
#	When a stream starts, find the movie script when possible and put it in a file in the movie folder
#
#SETUP:
#In Tautulli, go to Settings -> Notification Agents -> Add a new notification agent -> Script
#	Configuration:
#		Script Folder = folder where this script is stored
#		Script File = select this script
#		Script Timeout = 30
#		Description is optional
#	Triggers:
#		Playback Start = check
#	Conditions:
#		Media Type is movie
#	Arguments:
#		Playback Start -> Script Arguments = {title} {file}
#SAVE

if [[ -f "$(dirname "$2")/$1_script.txt" ]]
then
	exit 0
fi

link=$(curl -sL "https://imsdb.com/search.php" --data-raw "search_query=$(echo "$1" | sed "s| |%20|g")&submit=Go%21" | grep -Pio "Search results for '$1'.*?href=\"\K/Movie Scripts/.*?html(?=\" title=\"[^\"]+\">$1)")
link=$(curl -sL "https://imsdb.com$(echo "$link" | sed "s| |%20|g")" | grep -Pio "/scripts/.*?\.html" | head -n 1)
script=$(curl -sL "https://imsdb.com$link" | grep -oz "<pre>.*</pre>" | sed -e "s|<b>||g" -e "s|</b>||g" -e "s|<pre>||g" -e "s|</pre>||g")
if [[ -n "$script" ]]
then
	echo "$script" > "$(dirname "$2")/$1_script.txt"
fi
