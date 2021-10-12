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
plex_api_token=xxxxxxxxxxxxxx
#The title of the playlist
playlist_name="TV Channel"

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

#-----

playlist_ratingkey=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/playlists?X-Plex-Token=$plex_api_token&playlistType=video&includeCollections=1" | jq -rM --arg TITLE "$playlist_name" 'first(.MediaContainer.Metadata[] | select(.title==$TITLE).ratingKey)' 2>/dev/null)
machine_id=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.machineIdentifier)
if [[ -z "$playlist_ratingkey" ]]
then
	#playlist doesn't exist yet; setting up one
	echo "playlist doesn't exist"
	curl -sL -X POST "http://$plex_ip:$plex_port/playlists?type=video&title=${playlist_name// /%20}&smart=0&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/&X-Plex-Token=$plex_api_token" >> /dev/null && echo "playlist made" || { echo "failed to make playlist"; exit 1; }
else
	#playlist exists
	echo "playlist exists: $playlist_ratingkey"
	playlist_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items?X-Plex-Token=$plex_api_token")
	mapfile -t playlist_series < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].grandparentRatingKey)
	mapfile -t playlist_episodes < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].ratingKey)
	mapfile -t playlist_item < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].playlistItemID)
	for level in "${playlist_series[@]}"
	do
		ondeck_series=("${ondeck_series[@]}" "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/$level?X-Plex-Token=$plex_api_token&includeOnDeck=1" | jq -rM 'first(.MediaContainer.Metadata[].OnDeck.Metadata.ratingKey)')")
	done
	for level in "${!playlist_episodes[@]}"
	do
		if [[ "${ondeck_series[$level]}" = null ]]
		then
			curl -sL -X DELETE "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items/${playlist_item[$level]}?X-Plex-Token=$plex_api_token" >> /dev/null

		elif [[ "${ondeck_series[$level]}" != "${playlist_episodes[$level]}" ]]
		then
			curl -sL -X DELETE "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items/${playlist_item[$level]}?X-Plex-Token=$plex_api_token" >> /dev/null
			curl -sL -X PUT "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items?X-Plex-Token=$plex_api_token&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/${ondeck_series[$level]}" >> /dev/null
		fi
	done
fi
