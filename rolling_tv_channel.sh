#!/bin/bash

#The use case of this script is the following:
#	Make a playlist with the ondeck-episodes of the series and keep the playlist updated so that it always the ondeck's
#	Shuffle the playlist to basically watch your ondeck

#SETUP:
#	Run the script every few minutes automated (advised to run the script every <6min) using something like crontab

#The ip-address of the plex server
plex_ip=xxx.xxx.xxx.xxx
#The port of the plex server
plex_port=xxxxx
#The api-token of the plex server
plex_api_token=xxxxxxxxxxxxxxxxxxxx
#The title of the playlist
playlist_name="TV Channel"
#Add the ratingkeys of the series below in the array
#HOW TO FIND THE RATINGKEY OF A SERIES:
#1. In the web app of plex, go to the information page of the series (where you see info about the series, it's seasons etc.)
#2. Look at the url and locate the following: "key=%2Flibrary%2Fmetadata%2F123"
#3. The rating key of the series is the last numbers (e.g. key=%2Flibrary%2Fmetadata%2F782 = 782)
#4. Add that number to the array below for every series that you want (e.g. series=("1666" "1973" "917") )
series=("1666" "1973" "917")

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

if [[ "${#series[@]}" -le 1 ]]
then
	echo "Error: add atleast 2 series; currently ${#series[@]} added"
	exit 1
fi

#-----

playlist_ratingkey=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/playlists?X-Plex-Token=$plex_api_token&playlistType=video&includeCollections=1" | jq -rM --arg TITLE "$playlist_name" 'first(.MediaContainer.Metadata[] | select(.title==$TITLE).ratingKey)' 2>/dev/null)
machine_id=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.machineIdentifier)
if [[ -z "$playlist_ratingkey" ]]
then
	#playlist doesn't exist yet; setting up one
	echo "playlist doesn't exist"
	unset ondeck_list
	for level in "${series[@]}"
	do
		ondeck_list=("${ondeck_list[@]}" "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/$level?X-Plex-Token=$plex_api_token&includeOnDeck=1" | jq -rM 'first(.MediaContainer.Metadata[].OnDeck.Metadata.ratingKey)')")
	done
	ondeck_list="$(echo "${ondeck_list[@]}" | sed -Ee "s|null||g" -e "s|( )+|%2C|g")"
	curl -sL -X POST "http://$plex_ip:$plex_port/playlists?type=video&title=${playlist_name// /%20}&smart=0&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/$ondeck_list&X-Plex-Token=$plex_api_token" >> /dev/null && echo "playlist made" || { echo "failed to make playlist"; exit 1; }
else
	#playlist exists
	echo "playlist exists: $playlist_ratingkey"
	playlist_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items?X-Plex-Token=$plex_api_token")
	mapfile -t current_series < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].grandparentRatingKey)
	mapfile -t current_playlist < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].ratingKey)
	mapfile -t current_item < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].playlistItemID)
	if [[ "${#current_series[@]}" -lt "${#series[@]}" ]]
	then
		for level in "${series[@]}"
		do
			if ! [[ " ${current_series[@]} " =~ " $level " ]]
			then
				current_series=("${current_series[@]}" "$level")
			fi
		done

	elif [[ "${#current_series[@]}" -gt "${#series[@]}" ]]
	then
		sed -i "s|^series=\(.*\)$|series=\($(echo "${current_series[@]}" | sed -Ee "s|\b|\"|g")\)|" "$0"
	fi
	unset ondeck_list
	for level in "${current_series[@]}"
	do
		ondeck_list=("${ondeck_list[@]}" "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/$level?X-Plex-Token=$plex_api_token&includeOnDeck=1" | jq -rM 'first(.MediaContainer.Metadata[].OnDeck.Metadata.ratingKey)')")
	done
	for level in "${!ondeck_list[@]}"
	do
		if [[ "${ondeck_list[$level]}" = null ]]
		then
			curl -sL -X DELETE "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items/${current_item[$level]}?X-Plex-Token=$plex_api_token" >> /dev/null

		elif [[ "${ondeck_list[$level]}" != "${current_playlist[$level]}" ]]
		then
			if [[ -n "${current_playlist[$level]}" ]]
			then
				curl -sL -X DELETE "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items/${current_item[$level]}?X-Plex-Token=$plex_api_token" >> /dev/null
			fi
			curl -sL -X PUT "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items?X-Plex-Token=$plex_api_token&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/${ondeck_list[$level]}" >> /dev/null
		fi
	done
fi
