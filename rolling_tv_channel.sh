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

#Insert ratingkeys of series to always monitor (for example running shows)
#HOW TO FIND RATINGKEY OF A SERIES
#1. In the plex web-ui (ip:32400/web or app.plex.tv), go to the series info page (info about series, list of seasons, actors, etc.)
#2. Look in the url and locate "key=%2Flibrary%2Fmetadata%2F[DIGITS]"
#3. The "[DIGITS]" is the rating key of the series that you will need to add below
#EXAMPLE:
#	url 1: key=%2Flibrary%2Fmetadata%2F583
#	url 2: key=%2Flibrary%2Fmetadata%2F1666
#	series=("583" "1666")
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

#-----

#find the ratingkey (= unique id of something) of the playlist; if the playlist doesn't exist, this variable will be empty
playlist_ratingkey=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/playlists?X-Plex-Token=$plex_api_token&playlistType=video&includeCollections=1" | jq -rM --arg TITLE "$playlist_name" 'first(.MediaContainer.Metadata[] | select(.title==$TITLE).ratingKey)' 2>/dev/null)
#find the machine identifier of the server
machine_id=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.machineIdentifier)
#if the $playlist_ratingkey variable is empty, it doesn't exist; otherwise the playlist exists
if [[ -z "$playlist_ratingkey" ]]
then
	#playlist doesn't exist yet; setting up one
	echo "playlist doesn't exist"
	#if the series array is populated, fill up the ondeck_series array with the ratingkeys of the ondeck-episodes of the series; otherwise an empty playlist will be made
	for level in "${series[@]}"
	do
		ondeck_series=("${ondeck_series[@]}" "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/$level?X-Plex-Token=$plex_api_token&includeOnDeck=1" | jq -rM 'first(.MediaContainer.Metadata[].OnDeck.Metadata.ratingKey)')")
	done
	ondeck_series="$(echo "${ondeck_series[@]}" | sed "s| |%2C|g")"
	#create the playlist using the plex api
	curl -sL -X POST "http://$plex_ip:$plex_port/playlists?type=video&title=${playlist_name// /%20}&smart=0&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/$ondeck_series&X-Plex-Token=$plex_api_token" >> /dev/null && echo "playlist made" || { echo "failed to make playlist"; exit 1; }
else
	#playlist exists
	echo "playlist exists: $playlist_ratingkey"
	#make the request once and save the output in a variable to use later to reduce network requests
	playlist_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items?X-Plex-Token=$plex_api_token")
	#get the ratingkeys of the series in the playlist
	mapfile -t playlist_series < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].grandparentRatingKey)
	#get the ratingkeys of the episodes of the series in the playlist
	mapfile -t playlist_episodes < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].ratingKey)
	#get the unique item id of the entry in the playlist
	mapfile -t playlist_item < <(echo "$playlist_output" | jq -rM .MediaContainer.Metadata[].playlistItemID)
	#create an array with the ratingkeys of the ondeck-episodes of the series.
	for level in "${playlist_series[@]}"
	do
		ondeck_series=("${ondeck_series[@]}" "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/$level?X-Plex-Token=$plex_api_token&includeOnDeck=1" | jq -rM 'first(.MediaContainer.Metadata[].OnDeck.Metadata.ratingKey)')")
		#if one of the entries is of one of the manual series, remove it from the array so that the array only holds not-present series
		mapfile -t series < <(echo "${series[@]}" | sed "s| |\n|g" | grep -v "^$level$")
	done
	#now add the ratingkeys of the ondeck-episodes of the manual series that aren't present in the playlist (yet)
	for level in "${series[@]}"
	do
		ondeck_series=("${ondeck_series[@]}" "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/$level?X-Plex-Token=$plex_api_token&includeOnDeck=1" | jq -rM 'first(.MediaContainer.Metadata[].OnDeck.Metadata.ratingKey)')")
	done
	#do the following loop for every ondeck-episode
	for level in "${!ondeck_series[@]}"
	do
		#check if the entry in the playlist for the series is equal to the ondeck-episode of that series; if there isn't any entry for the series while there is a ondeck-episode, it will also execute the commands below
		if [[ "${ondeck_series[$level]}" != "${playlist_episodes[$level]}" ]]
		then
			#if there is an entry for the series, remove it (e.g. there is an episode but it isn't the ondeck one)
			if [[ -n "${playlist_episodes[$level]}" ]]
			then
				curl -sL -X DELETE "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items/${playlist_item[$level]}?X-Plex-Token=$plex_api_token" >> /dev/null
			fi
			#if there is an episode to replace the entry with, add it (e.g. when it was the last episode of the series, there won't be anything to replace the entry with so don't add anything)
			if [[ "${ondeck_series[$level]}" != null ]]
			then
				curl -sL -X PUT "http://$plex_ip:$plex_port/playlists/$playlist_ratingkey/items?X-Plex-Token=$plex_api_token&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/${ondeck_series[$level]}" >> /dev/null
			fi
		fi
	done
fi
