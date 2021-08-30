#!/bin/bash

#The use case of this script is the following:
#	After you've selected a movie library, it will try to set the audio track language to english
#	if it was not already. It will do it for every movie inside that library.

plex_ip=xxx.xxx.xxx.xxx
plex_port=xxxxx
plex_api_key=xxxxxxxxxxetc.

#give the amount of channels that the script should search for and try to apply
channels=1 #e.g. 1 or 2 or 6 or 9 etc.

#--------------------------------------------

for level in curl jq
do
	if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
	then
		echo "Error: $level is not installed"
		exit 1
	fi
done

if ! [[ "$plex_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
	echo "Error: invalid ip-address given as value for \$plex_ip"
	exit 1
fi

if ! [[ "$plex_port" =~ ^[0-9]{1,5}$ ]]
then
	echo "Error: invalid port given as value for \$plex_port"
	exit 1
fi

if ! [[ "$plex_api_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
	echo "Error: invalid api-token given as value for \$plex_api_token"
	exit 1
fi

if ! [[ "$channels" =~ ^[0-9]+$ ]]
then
	echo "Error: invalid channel amount given as value for \$channels"
	exit 1
fi

#-----

mapfile -t libraries < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Directory[] | select(.type=="movie").title')
mapfile -t lib_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Directory[] | select(.type=="movie").key')
for level in "${!libraries[@]}"
do
	echo "$((level+1))^|^${libraries[$level]}"
done | column -tes "^"
unset library_selection
until [[ $library_selection -ge 1 ]] \
&& [[ $library_selection -le "${#libraries[@]}" ]] \
|| [[ "${library_selection,,}" = cancel ]]
do
	read -rp "cancel | Select a library to process (1/${#libraries[@]}): " library_selection
done
if [[ "${library_selection,,}" = cancel ]]
then
	exit 0

elif [[ $library_selection -ge 1 ]] \
&& [[ $library_selection -le ${#libraries[@]} ]]
then
	lib_key="${lib_keys[$((library_selection-1))]}"
fi

unset confirmation
until [[ "${confirmation,,}" =~ ^(y|n|yes|no)$ ]]
do
	read -rp "The script will try to set the audio to $channels channel audio for EVERY movie; Proceed (y|n)? " confirmation
done
if [[ "${confirmation,,}" =~ ^(n|no)$ ]]
then
	exit 0

elif [[ "${confirmation,,}" =~ ^(y|yes)$ ]]
then
	mapfile -t keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections/$lib_key/all?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Metadata[].key')
	for level in "${keys[@]}"
	do
		#do this for every movie in the library
		movie_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port$level?X-Plex-Token=$plex_api_token")
		mapfile -t part_id < <(echo "$movie_output" | jq -rM '.MediaContainer.Metadata[].Media[].Part[].id')
		for level_2 in "${part_id[@]}"
		do
			#do this for every part of that movie
			correct_channel_id=$(echo "$movie_output" | jq -rM --argjson CHANNELS "$channels" --argjson ID "$level_2" '.MediaContainer.Metadata[].Media[].Part[] | select(.id==$ID).Stream[] | select(.streamType==2 and .channels==$CHANNELS).id' | head -n 1)
			if [[ -z $(echo "$movie_output" | jq -rM --argjson CHANNELS "$channels" --argjson ID "$level_2" '.MediaContainer.Metadata[].Media[].Part[] | select(.id==$ID).Stream[] | select(.streamType==2 and .selected==true and .channels==$CHANNELS)') ]] \
			&& [[ -n "$correct_channel_id" ]]
			then
				#there isn't an $channels chann audio track selected eventhough there is one
				curl -sL -X PUT "http://$plex_ip:$plex_port/library/parts/$level_2?X-Plex-Token=$plex_api_token&audioStreamID=$correct_channel_id&allParts=1"
			fi
		done
	done
fi
