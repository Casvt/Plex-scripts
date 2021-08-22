#! /bin/bash

#ip-address of the main plex server
main_plex_ip=192.168.2.18
#port of the main plex server
main_plex_port=32400
#api token of the main plex server
main_plex_token=2q6mc5PegzUk1a12E_TR

#ip-address of the tautulli server that monitors the main plex server
main_tautulli_ip=192.168.2.18
#port of the tautulli server that monitors the main plex server
main_tautulli_port=8181
#api token of the tautulli server that monitors the main plex server
main_tautulli_token=8f823962d93a474281a0f74096a05358

#ip-address of the backup plex server
backup_plex_ip=192.168.2.19
#port of the backup plex server
backup_plex_port=32400
#api token of the backup plex server
backup_plex_token=yLFtdqAHgmst4CYpHm1h

session_id="$1"

#--------------------------------------------

#check if the _port variables are set correctly
for level in "$main_plex_port" "$main_tautulli_port" "$backup_plex_port"
do
	if ! [[ "$level" =~ ^[0-9]{1,5}$ ]]
	then
		echo "Error: $level is not a valid port"
		exit 1
	fi
done

#check if the _ip variables are set correctly
for level in "$main_plex_ip" "$main_tautulli_ip" "$backup_plex_ip"
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
if ! [[ "$main_tautulli_token" =~ ^[0-9a-z]{32,34}$ ]]
then
	echo "Error: $main_tautulli_token is not a valid tautulli token"
	exit 1
fi

#check if the scripts was launched with a session id as argument
if [[ -z "$session_id" ]]
then
	echo "Error: not session id given as argument"
	exit 1
fi

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

#note the title of the media
full_title=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).full_title')
#note the plex guid of the media
guid=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).guid')
#note the key of the media on the backup server ( search for $full_title and find the result that has the correct $guid on the backup server)
key=$(curl -sL -H 'accept: application/json' "http://$backup_plex_ip:$backup_plex_port/search?X-Plex-Token=$backup_plex_token&query=$full_title" | jq -rM --arg GUID "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID).key')
#note the player on which the media is showed
player=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).player')
#note the section id of the media (id of library)
section_id=$(curl -sL -H 'accept: application/json' "http://$backup_plex_ip:$backup_plex_port/search?X-Plex-Token=$backup_plex_token&query=$full_title" | jq -rM --arg GUID "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID).librarySectionID')

#if the media couldnt be found on the backup server, dont bother running the script for this stream
if [[ -z "$key" ]] \
|| [[ "$key" = null ]]
then
	exit 0
fi

#wait 20 seconds to avoid switching when the movie is just loading when starting it
#the idea is to only switch when buffering for 10 seconds in the middle of the movie, not at the start
echo "Waiting 20 seconds..."
sleep 20s
echo "Waited 20 seconds; the script will start monitoring the stream"
#when the stream with the session id cant be found anymore (the media ended), exit the script (a.k.a. when the media has ended, also end the script)
until [[ -z $(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).state' 2>/dev/null) ]]
do
	buffering_counter=0
	#check the state of the media (playing, paused, buffering)
	state=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).state')
	#when the media is buffering, act on it. otherwise sleep 5s and check again
	if [[ "$state" = "buffering" ]]
	then
		echo "The media is buffering; checking if it will be 10 seconds from now"
		#the media is buffering. were going to check every second for 10s what the state is. every time (a.k.a. second) the state is buffering, do +1
		for level in {1..10}
		do
			if [[ $(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).state') = "buffering" ]]
			then
				buffering_counter=$((buffering_counter+1))
			fi
			sleep 1s
		done
		echo "The script buffered for $buffering_counter of the 10 seconds"
		#if the counter is 10, then that means that for those 10 seconds, it was buffering for every one of them
		if [[ "$buffering_counter" = 10 ]]
		then
			#note how far you are in the media
			view_offset=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).view_offset')
			#use PlexAPI to stop the current stream on the main server
			echo "Stopping current stream from main server"
			echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.stop(mtype='video')" | python3 -
			#launch the same media on the same client from the backup server
			echo "Starting stream from backup server"
			echo "from plexapi.server import PlexServer
baseurl = 'http://$backup_plex_ip:$backup_plex_port'
token = '$backup_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID($section_id).get('$full_title')
client = plex.client(\"$player\")
client.playMedia(movie, offset=$view_offset, key=\"$key\")" | python3 -
			exit 0
		fi
	fi
	sleep 5s
done

exit 0
