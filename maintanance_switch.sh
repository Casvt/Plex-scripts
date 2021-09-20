#!/bin/bash

#The use case of this script is the following:
#	When using the "--on" argument, it will move all streams to the backup server if possible
#	When using the "--off" argument, it will move all the streams that were moved to the backup server by "--on" back to the main server

main_plex_ip=xxx.xxx.xxx.xxx
main_plex_port=xxxxx
main_plex_token=xxxxxxxetc.

backup_plex_ip=xxx.xxx.xxx.xxx
backup_plex_port=xxxxx
backup_plex_token=xxxxxxxetc

#--------------------------------------------

#check if the _port variables are set correctly
for level in "$main_plex_port" "$backup_plex_port"
do
	if ! [[ "$level" =~ ^[0-9]{1,5}$ ]]
	then
		echo "Error: $level is not a valid port"
		exit 1
	fi
done

#check if the _ip variables are set correctly
for level in "$main_plex_ip" "$backup_plex_ip"
do
	if ! [[ "$level" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
	then
		echo "Error: $level is not a valid ip-address"
		exit 1
	fi
done

#check if the _plex_token variables are set correctly
for level in "$main_plex_token" "$backup_plex_token"
do
	if ! [[ "$level" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
	then
		echo "Error: $level is not a valid plex token"
		exit 1
	fi
done

#check if the requirements are installed
for level in curl jq python3 python3-pip
do
	if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
	then
		echo "Error: $level is not installed"
		exit 1
	fi
done

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

if [[ "$1" = "--on" ]]
then
	#move streams from main to backup
	mapfile -t session_ids < <(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/status/sessions?X-Plex-Token=$main_plex_token" | jq -rM .MediaContainer.Metadata[].Session.id)
	for level in "${session_ids[@]}"
	do
		session_output=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/status/sessions?X-Plex-Token=$main_plex_token" | jq --arg ID "$level" '.MediaContainer.Metadata[] | select(.Session.id==$ID)')
		full_title=$(echo "$session_output" | jq -rM .title)
		main_key=$(echo "$session_output" | jq -rM .key)
		type=$(echo "$session_output" | jq -rM .type)
		player=$(echo "$session_output" | jq -rM .Player.title)
		section_id=$(echo "$session_output" | jq -rM .librarySectionID)
		tmdb_id=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port$main_key?X-Plex-Token=$main_plex_token" | jq -rM 'first(.MediaContainer.Metadata[].Guid[].id | select(contains("tmdb")))')
		mapfile -t backup_key_options < <(curl -sL -H 'accept: application/json' "http://$backup_plex_ip:$backup_plex_port/search?X-Plex-Token=$backup_plex_token&query=${full_title// /%20}" | jq -rM --arg ID "$tmdb_id" --arg TYPE "$type" '.MediaContainer.Metadata[] | select(.type==$TYPE).key')
		for level_2 in "${backup_key_options[@]}"
		do
			option_output=$(curl -sL -H 'Accept: application/json' "http://$backup_plex_ip:$backup_plex_port$level_2?X-Plex-Token=$backup_plex_token")
			if [[ "$(echo "$option_output" | jq -rM 'first(.MediaContainer.Metadata[].Guid[].id | select(contains("tmdb")))')" \
				= "$tmdb_id" ]]
			then
				backup_key=$(echo "$option_output" | jq -rM .MediaContainer.Metadata[].key)
				backup_section_id=$(echo "$option_output" | jq -rM .MediaContainer.librarySectionID)
				view_offset=$(echo "$session_output" | jq -rM .viewOffset)
				echo "Stopping current stream from main server"
				echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.stop(mtype='video')" | python3 -
				echo "Starting stream from backup server"
				echo "from plexapi.server import PlexServer
baseurl = 'http://$backup_plex_ip:$backup_plex_port'
token = '$backup_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID($backup_section_id).get('$full_title')
client = plex.client(\"$player\")
client.playMedia(movie, offset=$view_offset, key=\"$backup_key\")" | python3 -
				if ! [[ -f "maintanance_switch_streams.json" ]]
				then
					jq -n --arg PLAYER "$player" --arg SECTIONID "$section_id" --arg TITLE "$full_title" --arg KEY "$main_key" '[{"player": $PLAYER, "section_id": $SECTIONID, "title": $TITLE, "key": $KEY}]' > maintanance_switch_streams.json
				else
					cat "maintanance_switch_streams.json" | jq --arg PLAYER "$player" --arg SECTIONID "$section_id" --arg TITLE "$full_title" --arg KEY "$main_key" '. += [{"player": $PLAYER, "section_id": $SECTIONID, "title": $TITLE, "key": $KEY}]' > maintanance_switch_streams.json
				fi
				break
			fi
		done
	done

elif [[ "$1" = "--off" ]]
then
	#move streams originating from main from backup to main back
	if ! [[ -f "maintanance_switch_streams.json" ]]
	then
		echo "Error: no maintanance_switch_streams.json file found (which is needed)"
		exit 1
	fi
	jq 'keys[]' < maintanance_switch_streams.json | \
	while read -r level
	do
		mapfile -t info < <(jq --arg INDEX "$level" '.[$INDEX] | .player, .sectiond_id, .title, .key')
		view_offset=$(curl -sL -H 'Accept: application/json' "http://$backup_plex_ip:$backup_plex_port/status/sessions?X-Plex-Token=$backup_plex_token" | jq -rM --arg PLAYER "${info[0]}" --arg SECTIONID "${info[1]}" '.MediaContainer.Metadata[] | select(.Player.title==$PLAYER and .librarySectionID==$SECTIONID and .title==$TITLE).viewOffset')
		echo "Stopping current stream from backup server"
		echo "from plexapi.server import PlexServer
baseurl = 'http://$backup_plex_ip:$backup_plex_port'
token = '$backup_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"${info[0]}\")
client.stop(mtype='video')" | python3 -
		echo "Starting stream from main server"
		echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID(${info[1]}).get('${info[2]}')
client = plex.client(\"${info[0]}\")
client.playMedia(movie, offset=$view_offset, key=\"${info[3]}\")" | python3 -
	done
	rm "maintanance_switch_streams.json"

else
	echo "Error: Give \"--on\" or \"--off\" as an argument to enable/disable maintanance mode"
	exit 1
fi
