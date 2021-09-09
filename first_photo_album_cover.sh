#!/bin/bash

#The use case of this script is the following:
#   The first image in an album will be made the cover of the album.
#   This script applies to every album in every directory (a.k.a every album that exists on your plex server)

#ip-address of the plex server
plex_ip=xxx.xxx.xxx.xxx
#port of the plex server
plex_port=xxxxx
#api token of the plex server
plex_api_token=xxxxxxxxxetc

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

list_output=$(pip3 list)
for level in "PlexAPI"
do
	if ! echo "$list_output" | tac | grep -q "^$level"
	then
		echo "Error: $level is not installed; use pip3"
		exit 1
	fi
done

#-----

mapfile -t lib_ids < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Directory[] | select(.type=="photo").key')
for level in "${lib_ids[@]}"
do
    mapfile -t album_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections/$level/folder?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.Metadata[].key)
    for level_2 in "${album_keys[@]}"
    do
        poster_path=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port$level_2&X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.Metadata[0].Media[].Part[].file | head -n 1)
        echo "from plexapi.server import PlexServer
baseurl = 'http://$plex_ip:$plex_port'
token = '$plex_api_token'
plex = PlexServer(baseurl, token)

album = plex.fetchItem($(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port$level_2&X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.Metadata[0].parentRatingKey))
album.uploadPoster(filepath='$poster_path')" | python3 -
    done
done