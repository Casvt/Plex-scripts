#! /bin/bash

#The use case of this script is the following:
#	If you're streaming media from the main plex server to a client and the stream starts buffering for atleast 10 seconds,
#	then it will switch over to streaming that media from the backup server.
#	That means that if the media that you're watching has been buffering (loading) for more than 10 seconds,
#	it will stop the stream and start a new one from the backup plex server
#	It will only switch over when the media has been found on the backup server.
#
#SETUP:
#In Tautulli, go to Settings -> Notification Agents -> Add a new notification agent -> Script
#	Configuration:
#		Script Folder = folder where this script is stored
#		Script File = select this script
#		Script Timeout = 0
#		Description is optional
#	Triggers:
#		Playback Start = check
#	Arguments:
#		Playback Start -> Script Arguments = {session_id}
#SAVE

#ip-address of the main plex server
main_plex_ip=xxx.xxx.xxx.xxx
#port of the main plex server
main_plex_port=xxxxx
#api token of the main plex server
main_plex_token=xxxxxxxxxetc.

#ip-address of the tautulli server that monitors the main plex server
main_tautulli_ip=xxx.xxx.xxx.xxx
#port of the tautulli server that monitors the main plex server
main_tautulli_port=xxxx
#api token of the tautulli server that monitors the main plex server
main_tautulli_token=xxxxxxxxxetc.

#OPTIONAL
#ip-address of the backup plex server
backup_plex_ip=
#port of the backup plex server
backup_plex_port=
#api token of the backup plex server
backup_plex_token=

session_id="$1"

#--------------------------------------------

#check if the _port variables are set correctly
for level in "$main_plex_port" "$main_tautulli_port"
do
	if ! [[ "$level" =~ ^[0-9]{1,5}$ ]]
	then
		echo "Error: $level is not a valid port"
		exit 1
	fi
done

#check if the _ip variables are set correctly
for level in "$main_plex_ip" "$main_tautulli_ip"
do
	if ! [[ "$level" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
	then
		echo "Error: $level is not a valid ip-address"
		exit 1
	fi
done

#check if the _plex_token variables are set correctly
for level in "$main_plex_token"
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

#check if the backup_plex_ip variable is set correctly when used
if ! [[ "$backup_plex_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]] \
&& [[ -n "$backup_plex_ip" ]]
then
	echo "Error: $backup_plex_ip is not a valid backup plex ip-address"
	exit 1
fi

#check if the backup_plex_port variable is set correctly when used
if ! [[ "$backup_plex_port" =~ ^[0-9]{1,5}$ ]] \
&& [[ -n "$backup_plex_port" ]]
then
	echo "Error: $backup_plex_port is not a valid backup plex port"
	exit 1
fi

#check if the backup_plex_token variable is set correctly when used
if ! [[ "$backup_plex_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]] \
&& [[ -n "$backup_plex_token" ]]
then
	echo "Error: $backup_plex_token is not a valid backup plex token"
	exit 1
fi.

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

#set the resolution "ladder"
res_lad[8000]=1
res_lad[6000]=2
res_lad[4000]=3
res_lad[2000]=4
res_lad[1080]=5
res_lad[720]=6
res_lad[480]=7

#-----

#note the title of the media
full_title=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).full_title')
#note the plex guid of the media
guid=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).guid')
#note the player on which the media is showed
player=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).player')
#note rating key of media on main server
rating_key=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).rating_key')
#note the current resolution the media is playing at
current_res=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).stream_video_full_resolution')
#note the librarySectionID of the media library
lib_key=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/library/metadata/$rating_key?X-Plex-Token=$main_plex_token" | jq -rM .MediaContainer.Metadata[].librarySectionID)

#1. check if theres a better version available.
mapfile -t versions_res < <(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/library/metadata/$rating_key?X-Plex-Token=$main_plex_token" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
for level in "${versions_res[@]}"
do
	level=$(echo "$level" | sed -e "s|k$|000|" -e "s|p$||")
	if [[ "${res_lad[$level]}" -lt "${res_lad[$current_res]}" ]]
	then
		#same library but higher version was found
		exit 0
	fi
done

#2. check if theres a better version in another library.
mapfile -t alternate_lib_keys < <(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/search?X-Plex-Token=$main_plex_token&query=$(echo "$full_title" | sed "s| |%20|g")" | jq -rM --argjson "LIBKEY" "$lib_key" --arg "GUID" "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID) | select(.librarySectionID!=$LIBKEY).key')
for level in "${alternate_lib_keys[@]}"
do
	movie_output=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port$level?X-Plex-Token=$main_plex_token")
	mapfile -t avail_res < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
	mapfile -t avail_id < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].id)
	for level_2 in "${!avail_res[@]}"
	do
		avail_res[$level_2]}=$(echo "${avail_res[$level_2]}" | sed -e "s|k$|000|" -e "s|p$||")
		if [[ "${res_lad[${avail_res[$level_2]}]}" -lt "${res_lad[$current_res]}" ]]
		then
			#different library but higher version was found
			key="$level"
			media_id="${avail_id[$level_2]}"
			section_id=$(echo "$movie_output" | jq .MediaContainer.Metadata[].librarySectionID)
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
			#launch the same media on the same client from the main server
			echo "Starting stream from main server"
			echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID($section_id).get('$full_title')
client = plex.client(\"$player\")
client.playMedia(movie, offset=$view_offset, key=\"$key\")" | python3 -
			#set the videostream to the correct one
#			echo "from plexapi.server import PlexServer
#baseurl = 'http://$main_plex_ip:$main_plex_port'
#token = '$main_plex_token'
#plex = PlexServer(baseurl, token)
#
#client = plex.client(\"$player\")
#client.setVideoStream(videoStreamID='$media_id', mtype='video')" | python3 -
			exit 0
		fi
	done
done

#3. check if theres a better version on the backup server if setup
if [[ -n "$backup_plex_ip" ]] \
&& [[ -n "$backup_plex_port" ]] \
&& [[ -n "$backup_plex_token" ]]
then
mapfile -t alternate_lib_keys < <(curl -sL -H 'Accept: application/json' "http://$backup_plex_ip:$backup_plex_port/search?X-Plex-Token=$backup_plex_token&query=$(echo "$full_title" | sed "s| |%20|g")" | jq -rM --argjson "LIBKEY" "$lib_key" --arg "GUID" "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID) | select(.librarySectionID!=$LIBKEY).key')
for level in "${alternate_lib_keys[@]}"
do
	movie_output=$(curl -sL -H 'Accept: application/json' "http://$backup_plex_ip:$backup_plex_port$level?X-Plex-Token=$backup_plex_token")
	mapfile -t avail_res < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
	mapfile -t avail_id < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].id)
	for level_2 in "${!avail_res[@]}"
	do
		avail_res[$level_2]=$(echo "${avail_res[$level_2]}" | sed -e "s|k$|000|" -e "s|p$||")
	    if [[ "${res_lad[${avail_res[$level_2]}]}" -lt "${res_lad[$current_res]}" ]]
	    then
	        #different library but higher version was found
	        key="$level"
	        media_id="${avail_id[$level_2]}"
	        section_id=$(echo "$movie_output" | jq .MediaContainer.Metadata[].librarySectionID)
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
			#set the videostream to the correct one
#			echo "from plexapi.server import PlexServer
#baseurl = 'http://$backup_plex_ip:$backup_plex_port'
#token = '$backup_plex_token'
#plex = PlexServer(baseurl, token)
#
#client = plex.client(\"$player\")
#client.setVideoStream(videoStreamID='$media_id', mtype='video')" | python3 -
	        exit 0
	    fi
	done
done
fi

exit 0