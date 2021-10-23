#!/bin/bash

#made after this suggestion
#https://www.reddit.com/r/PleX/comments/pbwf41/ill_make_any_script_suggestions_you_give/haf6660?utm_source=share&utm_medium=web2x&context=3

#used for converting an m3u file to a plex playlist

plex_ip=xxx.xxx.xxx.xxx
plex_port=xxxxx
plex_api_token=xxxxxxxxetc.

#--------------------------------------------

if ! [[ "$plex_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
	echo "Error: not a valid ip"
	exit 1
fi

if ! [[ "$plex_port" =~ ^[0-9]{1,5}$ ]]
then
	echo "Error: not a valid port"
	exit 1
fi

if ! [[ "$plex_api_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
	echo "Error: not a valid api token"
	exit 1
fi

for level in curl
do
	if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
	then
		echo "Error: $level is not installed"
		exit 1
	fi
done

#-----

sections_output=$(curl -sL "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token")
mapfile -t uuid < <(echo "$sections_output" | grep -Po "uuid=\"\K.*?(?=\")")
for level in ${!uuid[@]}
do
	echo "$((level+1))^|^$(echo "$sections_output" | grep -Po "title=\"\K.*?(?=\".*uuid=\"${uuid[$level]})")"
done | column -tes "^"

unset library_selection
until [[ $library_selection -ge 1 ]] \
&& [[ $library_selection -le ${#uuid[@]} ]] \
|| [[ "${library_selection,,}" = cancel ]]
do
	read -rp "cancel | Select library (1/${#uuid[@]}): " library_selection
done

if [[ ${library_selection,,} = cancel ]]
then
	exit 0

elif [[ $library_selection -ge 1 ]] \
&& [[ $library_selection -le ${#uuid[@]} ]]
then
	library_key=$(echo "$sections_output" | grep -Po "key=\"\K\d+(?=\".*uuid=\"${uuid[$((library_selection-1))]})")
fi

unset folder
until [[ -f "$folder" ]] \
&& [[ "$folder" =~ "\.m3u$" ]] \
|| [[ "${folder,,}" = cancel ]]
do
	read -rp "cancel | Give the path to the .m3u file: " folder
done

if [[ ${folder,,} = cancel ]]
then
	exit 0

else
	curl -sL -X POST "http://$plex_ip:$plex_port/playlists/upload?sectionID=$library_key&path=$folder&X-Plex-Token=$plex_api_token" && exit 0 || exit 1
fi
