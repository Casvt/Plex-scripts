#!/bin/bash

#The use case of this script is the following:
#	Distribute streams originally started on the main server between two servers.
#	The script will try its hardest to keep the amount of streams on both servers almost equal.

#SETUP:
#In Tautulli, go to Settings -> Notification Agents -> Add a new notification agent -> Script
#       Configuration:
#               Script Folder = folder where this script is stored
#               Script File = select this script
#               Script Timeout = 60
#               Description is optional
#       Triggers:
#               Playback Start = check
#		Playback Stop = check
#       Arguments:
#               Playback Start -> Script Arguments = {session_id}
#		Playback Stop -> Script Arguments = -s
#SAVE

#If there are an uneven amount of streams (e.g. 3-2), where should that last stream be placed?
prefered=main #main/backup

main_plex_ip=xxx.xxx.xxx.xxx
main_plex_port=xxxxx
main_plex_token=xxxxxxxxxxetc.

main_tautulli_ip=xxx.xxx.xxx.xxx
main_tautulli_port=xxxx
main_tautulli_token=xxxxxxxxxetc.

backup_plex_ip=xxx.xxx.xxx.xxx
backup_plex_port=xxxxx
backup_plex_token=xxxxxxxxxetc.

backup_tautulli_ip=xxx.xxx.xxx.xxx
backup_tautulli_port=xxxx
backup_tautulli_token=xxxxxxxxetc.

#--------------------------------------------

#check if the _port variables are set correctly
for level in "$main_plex_port" "$main_tautulli_port" "$backup_plex_port" "$backup_tautulli_port"
do
        if ! [[ "$level" =~ ^[0-9]{1,5}$ ]]
        then
                echo "Error: $level is not a valid port"
                exit 1
        fi
done

#check if the _ip variables are set correctly
for level in "$main_plex_ip" "$main_tautulli_ip" "$backup_plex_ip" "$backup_tautulli_ip"
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

#check if the main_tautulli_token variable is set correctly
for level in "$main_tautulli_token" "$backup_tautulli_token"
do
	if ! [[ "$level" =~ ^[0-9a-z]{32,34}$ ]]
	then
	        echo "Error: $level is not a valid tautulli token"
	        exit 1
	fi
done

#check if the prefered variable is set correctly
if ! [[ "$prefered" =~ ^(main|backup)$ ]]
then
	echo "Error: $prefered is not a valid value for a prefered server"
	exit 1
fi

#-----

date >> balancer_output
if [[ "$1" = "-s" ]]
then
	echo "Stream stopped" >> balancer_output
	stream_end=true
	unset session_id
else
	echo "Stream started" >> balancer_output
	session_id="$1"
	unset stream_end
fi

if [[ -z "$stream_end" ]]
then
	main_session_amount=$(($(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM '.response.data.sessions | length')-1))
else
	main_session_amount=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM '.response.data.sessions | length')
fi
backup_session_amount=$(curl -sL "http://$backup_tautulli_ip:$backup_tautulli_port/api/v2?apikey=$backup_tautulli_token&cmd=get_activity" | jq -rM '.response.data.sessions | length')
echo "Balance: $main_session_amount | $backup_session_amount" >> balancer_output

switch_over()
{
	#use PlexAPI to stop the current stream on the main server
        echo "		Stopping current stream from main server" >> balancer_output
        echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.stop(mtype='video')" | python3 - || return 1
        #launch the same media on the same client from the backup server
        echo "		Starting stream from backup server" >> balancer_output
        echo "from plexapi.server import PlexServer
baseurl = 'http://$backup_plex_ip:$backup_plex_port'
token = '$backup_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID($section_id).get('$full_title')
client = plex.client(\"$player\", identifier=\"$machine_id\")
client.playMedia(movie, offset=$view_offset, key=\"$key\")" | python3 -
}

reverse_switch_over()
{
	#use PlexAPI to stop the current stream on the backup server
        echo "		Stopping current stream from backup server" >> balancer_output
        echo "from plexapi.server import PlexServer
baseurl = 'http://$backup_plex_ip:$backup_plex_port'
token = '$backup_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\", identifier=\"$machine_id\")
client.stop(mtype='video')" | python3 - || return 1
        #launch the same media on the same client from the main server
        echo "		Starting stream from main server" >> balancer_output
        echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID($section_id).get('$full_title')
client = plex.client(\"$player\")
client.playMedia(movie, offset=$view_offset, key=\"$key\")" | python3 -
}

if [[ -z "$stream_end" ]]
then
	#stream started; if needed, redirect it to balance the streams
	if [[ "$main_session_amount" -gt "$backup_session_amount" ]] \
	|| [[ "$main_session_amount" -eq "$backup_session_amount" \
		&& "$prefered" = backup ]]
	then
		echo "Moving stream to backup server:" >> balancer_output
		#move session to backup server
		activity_output=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity")
		{ echo "$session_id"; echo "$activity_output" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id!=$ID).session_id'; } | \
		while read -r level
		do
			echo "	$level" >> balancer_output
			if [[ $(echo "$activity_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).location') != "lan" ]]
			then
				echo "		Not local" >> balancer_output
				continue
			fi
			#note the title of the media
			full_title=$(echo "$activity_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).full_title')
			#note the plex guid of the media
			guid=$(echo "$activity_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).guid')
			#note the key of the media on the backup server ( search for $full_title and find the result that has the correct $guid on the backup server)
			key=$(curl -sL -H 'accept: application/json' "http://$backup_plex_ip:$backup_plex_port/search?X-Plex-Token=$backup_plex_token&query=$full_title" | jq -rM --arg GUID "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID).key')
			if [[ -z "$key" ]] \
			|| [[ "$key" = null ]]
			then
				echo "		No key found" >> balancer_output
				continue
			fi
			#note the player on which the media is showed
			player=$(echo "$activity_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).player')
			machine_id=$(echo "$activity_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).machine_id')
			#note the section id of the media on the backup server (id of library)
			section_id=$(curl -sL -H 'accept: application/json' "http://$backup_plex_ip:$backup_plex_port/search?X-Plex-Token=$backup_plex_token&query=$full_title" | jq -rM --arg GUID "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID).librarySectionID')
			#note the view offset of the playing media
			view_offset=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).view_offset')
			#switch over
			switch_over || { echo "		Couldnt stop the stream" >> balancer_output; continue; }
			exit 0
		done
	fi
else
	#stream stopped; if needed, rebalance current streams
	if [[ "$((main_session_amount+1))" -lt "$backup_session_amount" ]] \
	|| [[ "$((main_session_amount+1))" -eq "$backup_session_amount" \
		&& "$prefered" = main ]]
	then
		echo "Moving stream to main server:" >> balancer_output
		#move session to main server
		backup_tautulli_session_output=$(curl -sL "http://$backup_tautulli_ip:$backup_tautulli_port/api/v2?apikey=$backup_tautulli_token&cmd=get_activity")
		echo "$backup_tautulli_session_output" | jq -rM '.response.data.sessions[].session_id' | \
		while read -r level
		do
			echo "	$level" >> balancer_output
			if [[ $(echo "$backup_tautulli_session_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).location') != "lan" ]]
            then
				echo "		Not local" >> balancer_output
                continue
            fi
			#note the title of the media
			full_title=$(echo "$backup_tautulli_session_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).full_title')
			#note the plex guid of the media
			guid=$(echo "$backup_tautulli_session_output" | jq -rM --arg ID '.response.data.sessions[] | select(.session_id==$ID).guid')
			#note the key of the media on the backup server ( search for $full_title and find the result that has the correct $guid on the backup server)
			key=$(curl -sL -H 'accept: application/json' "http://$main_plex_ip:$main_plex_port/search?X-Plex-Token=$main_plex_token&query=$full_title" | jq -rM --arg GUID "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID).key')
			if [[ -z "$key" ]] \
			|| [[ "$key" = null ]]
			then
				echo "		No key found" >> balancer_output
				continue
			fi
			#note the player on which the media is showed
			player=$(echo "$backup_tautulli_session_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).player')
			machine_id=$(echo "$backup_tautulli_session_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).machine_id')
			#note the section id of the media on the main server (id of library)
			section_id=$(curl -sL -H 'accept: application/json' "http://$main_plex_ip:$main_plex_port/search?X-Plex-Token=$main_plex_token&query=$full_title" | jq -rM --arg GUID "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID).librarySectionID')
			#note the view offset of the playing media
			view_offset=$(echo "$backup_tautulli_session_output" | jq -rM --arg ID "$level" '.response.data.sessions[] | select(.session_id==$ID).view_offset')
			#switch over
			reverse_switch_over || { echo "		Couldnt stop the stream" >> balancer_output; continue; }
			exit 0
		done
	fi
fi
