#! /bin/bash

#The use case of this script is the following:
#	When you start a stream, this script will be launched.
#	It will check if there's a higher resolution version available of the media.
#	This higher resolution version can be selected on the same page, in a different library or on your backup server.
#	If the script found a higher resolution version, it will, depending on the location, change the stream to stream that file.
#
#SETUP:
#In Tautulli, go to Settings -> Notification Agents -> Add a new notification agent -> Script
#	Configuration:
#		Script Folder = folder where this script is stored
#		Script File = select this script
#		Script Timeout = 60
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

#These are exclution variables. Everything you put here will be excluded from upgrading
#Give the library sectionid's of the libraries to not upgrade >from< (e.g. If you stream a movie that is in the "4K movies - no upgrade" library and add the library's id in the array, it will not upgrade that movie, as it is coming from a library that is excluded)
ex_library_source_ids=()
#Give the library sectionid's of the libraries to not upgrade >to< (e.g. You're streaming from Library1 and the script found a better version in Library2. If you have the id of Library2 added to the array below, it will not upgrade as that library is excluded from upgrading to)
ex_library_target_ids=()
#Exactly the same as ex_library_target_ids but then for library sectionid's of the backup server. So library sectionid's that you enter here will be ignored/avoided on the backup server
#Only used/useful when the backup plex server is setup
ex_library_remote_target_ids=()
#Give the rating keys of the media to ignore (e.g. if you stream Movie1 and added it's rating key below, it will not upgrade it)
ex_media_rating_keys=()
#Give resolutions to not upgrade from (e.g. upgrade everything unless it's a 720p stream -> add 720 to array)
#IMPORTANT: fill in the correct name for the resolution
#name       | value for array
#480p       | 480
#720p       | 720
#1080p      | 1080
#1440p (2k) | 2000
#4k         | 4000
#6k         | 6000
#8k         | 8000
ex_resolutions=()

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
fi

#check if the scripts was launched with a session id as argument
if [[ -z "$session_id" ]]
then
	echo "Error: not session id given as argument"
	exit 1
fi

#check if the exclusion variables are set correctly
if [[ -n "${ex_library_source_ids[@]}" ]]
then
	for level in "${ex_library_source_ids[@]}"
	do
		if ! [[ "$level" =~ ^[0-9]+$ ]]
		then
			echo "Error: $level is not a valid librarysection id inside the ex_library_source_ids array"
			exit 1
		fi
	done
fi
if [[ -n "${ex_library_target_ids[@]}" ]]
then
	for level in "${ex_library_target_ids[@]}"
	do
		if ! [[ "$level" =~ ^[0-9]+$ ]]
		then
			echo "Error: $level is not a valid librarysection id inside the ex_library_target_ids array"
			exit 1
		fi
	done
fi
if [[ -n "${ex_media_rating_keys[@]}" ]]
then
	for level in "${ex_media_rating_keys[@]}"
	do
		if ! [[ "$level" =~ ^[0-9]+$ ]]
		then
			echo "Error: $level is not a valid ratingkey inside the ex_media_rating_keys array"
			exit 1
		fi
	done
fi
if [[ -n "${ex_resolutions[@]}" ]]
then
	for level in "${ex_resolutions[@]}"
	do
		if ! [[ "$level" =~ ^(480|720|1080|(2|4|6|8)000)$ ]]
		then
			echo "Error: $level is not a valid resolution inside the ex_resolutions array"
			exit 1
		fi
	done
fi
if [[ -n "$backup_plex_ip" ]] \
&& [[ -n "$backup_plex_port" ]] \
&& [[ -n "$backup_plex_token" ]]
then
	if [[ -n "${ex_library_remote_target_ids[@]}" ]]
	then
		for level in "${ex_library_remote_target_ids[@]}"
		do
			if ! [[ "$level" =~ ^[0-9]+$ ]]
			then
				echo "Error: $level is not a valid librarysection id inside the ex_library_remote_target_ids array"
				exit 1
			fi
		done
	fi
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
current_res=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).stream_video_full_resolution' | sed -e "s|k$|000|" -e "s|p$||")
#note the librarySectionID of the media library
lib_key=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/library/metadata/$rating_key?X-Plex-Token=$main_plex_token" | jq -rM .MediaContainer.Metadata[].librarySectionID)

#0. check if the stream falls under any exclusions; if so, exit
if [[ " ${ex_resolutions[@]} " =~ "$current_res" ]] \
|| [[ " ${ex_library_ids[@]} " =~ "$lib_key" ]] \
|| [[ " ${ex_media_rating_keys[@]} " =~ "$rating_key" ]]
then
	exit 0
fi

#1. check if theres a better version available.
movie_output=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/library/metadata/$rating_key?X-Plex-Token=$main_plex_token")
mapfile -t avail_res < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
mapfile -t avail_media_id < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].id)
for level in "${avail_media_id[@]}"
do
	avail_id=("${avail_id[@]}" "$(echo "$movie_output" | jq -rM --argjson ID "$level" '.MediaContainer.Metadata[].Media[] | select(.id==$ID).Part[].Stream[] | select(.streamType==1).id' | head -n 1)")
done
for level in "${!avail_res[@]}"
do
	avail_res[$level]=$(echo "${avail_res[$level]}" | sed -e "s|k$|000|" -e "s|p$||")
	if [[ "${res_lad[${avail_res[$level]}]}" -lt "${res_lad[$current_res]}" ]]
	then
		#same library but higher version was found
		media_id="${avail_id[$level]}"
		#set the videostream to the correct one
		echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.setVideoStream(videoStreamID=$media_id, mtype='video')" | python3 -
		exit 0
	fi
done

#2. check if theres a better version in another library.
mapfile -t alternate_lib_keys < <(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/search?X-Plex-Token=$main_plex_token&query=$(echo "$full_title" | sed "s| |%20|g")" | jq -rM --argjson "LIBKEY" "$lib_key" --arg "GUID" "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID) | select(.librarySectionID!=$LIBKEY).key')
for level in "${alternate_lib_keys[@]}"
do
	movie_output=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port$level?X-Plex-Token=$main_plex_token")
	if [[ " ${ex_library_target_ids[@]} " =~ "$(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].librarySectionID)" ]]
	then
		continue
	fi
	mapfile -t avail_res < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
	mapfile -t avail_media_id < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].id)
	for level_2 in "${avail_media_id[@]}"
	do
		avail_id=("${avail_id[@]}" "$(echo "$movie_output" | jq -rM --argjson ID "$level_2" '.MediaContainer.Metadata[].Media[] | select(.id==$ID).Part[].Stream[] | select(.streamType==1).id' | head -n 1)")
	done
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
			echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.setVideoStream(videoStreamID=$media_id, mtype='video')" | python3 -
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
		if [[ " ${ex_library_remote_target_ids[@]} " =~ "$(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].librarySectionID)" ]]
		then
			continue
		fi
		mapfile -t avail_res < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
		mapfile -t avail_media_id < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].id)
		for level_2 in "${avail_media_id[@]}"
		do
			avail_id=("${avail_id[@]}" "$(echo "$movie_output" | jq -rM --argjson ID "$level_2" '.MediaContainer.Metadata[].Media[] | select(.id==$ID).Part[].Stream[] | select(.streamType==1).id' | head -n 1)")
		done
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
				echo "from plexapi.server import PlexServer
baseurl = 'http://$backup_plex_ip:$backup_plex_port'
token = '$backup_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.setVideoStream(videoStreamID=$media_id, mtype='video')" | python3 -
		        exit 0
		    fi
		done
	done
fi

exit 0
