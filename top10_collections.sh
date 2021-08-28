#!/bin/bash

#The use case of this script is the following:
#	Run this script to add a collection with the 10 most popular movies according to tautulli
#	It is intented to run every so often (use crontab to run it every 12 hours for example)
#
#The name of the collection is "Top 10 movies"

#ip address of the plex server
plex_ip=xxx.xxx.xxx.xxx
#port of the plex server
plex_port=xxxxx
#api token of the plex server
plex_api_token=xxxxxxxxetc.

#ip address of the tautulli server
tautulli_ip=xxx.xxx.xxx.xxx
#port of the tautulli server
tautulli_port=xxxx
#api token of the tautulli server
tautulli_api_token=xxxxxxxxxxxetc.

#the id of the library to add the collection to
section_id=x

#--------------------------------------------

if ! [[ "$plex_port" =~ ^[0-9]{1,5}$ ]]
then
	echo "Error: $level is not a valid port"
	exit 1
fi

if ! [[ "$plex_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
	echo "Error: $level is not a valid ip-address"
	exit 1
fi

if ! [[ "$plex_api_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
	echo "Error: $level is not a valid plex token"
	exit 1
fi

for level in curl jq
do
	if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
	then
		echo "Error: $level is not installed"
		exit 1
	fi
done

#-----

id=$(curl -sL "http://$plex_ip:$plex_port/library/sections/$section_id/collections?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Metadata[] | select(.title=="Top 10 movies").ratingKey' 2>/dev/null)
if [[ $? = 0 ]]
then
	curl -sL -X DELETE "http://$plex_ip:$plex_port/library/collections/$id?X-Plex-Token=$plex_api_token"
fi

mapfile -t ratingkeys < <(curl -sL "http://$tautulli_ip:$tautulli_port/api/v2?apikey=$tautulli_api_token&cmd=get_home_stats&stat_id=top_movies" | jq .response.data.rows[].rating_key)
machine_id=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.machineIdentifier)
curl -sL -X POST "http://$plex_ip:$plex_port/library/collections?type=1&title=Top%2010%20movies&smart=0&sectionId=$section_id&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/$(echo "${ratingkeys[@]}" | sed -E "s|\b \b|,|g")&X-Plex-Token=$plex_api_token"
