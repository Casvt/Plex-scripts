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
main_tautulli_token=xxxxxxxxxxxxxxetc.

#OPTIONAL
#ip-address of the backup plex server
backup_plex_ip=
#port of the backup plex server
backup_plex_port=
#api token of the backup plex server
backup_plex_token=

#Enable parts of the script
audio_upgrading=true #true/false
video_upgrading=true #true/false

#These are inclusion variables. Only streams that match these variables are influenced
#IMPORTANT: Inclusion variables OVERRULE exclusion variables.
#Give the library sectionid's of the only libraries to upgrade >from<
in_library_source_ids=()
#Give the library sectionid's of the only libraries to upgrade >to<
in_library_target_ids=()
#Exactly the same as ex_library_target_ids but then for library sectionid's of the backup server.
#Only used/useful when the backup plex server is setup
in_library_remote_target_ids=()
#Give the rating keys of the only media to influence.
in_media_rating_keys=()
#Give resolutions to only upgrade from (e.g. upgrade nothing exept a 720p stream -> add 720 to array)
#IMPORTANT: fill in the correct name for the resolution
#name       | value for array
#480p       | 480
#720p       | 720
#1080p      | 1080
#1440p (2k) | 2000
#4k         | 4000
#6k         | 6000
#8k         | 8000
in_resolutions=()
#Give audio channels to only upgrade from (e.g. upgrade nothing exept 5.1 channel audio -> add 6 to array)
#IMPORTANT: fill in the total amount of channels (e.g. 5.1 = 6, 7.1.2 = 10, etc.)
in_channels=()
#Give client names to only upgrade audio on
audio_in_clients=()
#Give client names to only upgrade video on
video_in_clients=()

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
#Give audio channels to not upgrade from (e.g. upgrade everything unless it's 5.1 channel audio -> add 6 to array)
#IMPORTANT: fill in the total amount of channels (e.g. 5.1 = 6, 7.1.2 = 10, etc.)
ex_channels=()
#Give client names to not upgrade audio on (e.g. dont upgrade if the stream is on the "Bedroom Shield" -> add "Bedroom Shield" to array)
audio_ex_clients=()
#Give client names to not upgrade video on
video_ex_clients=()

#example:
#only apply the script when it's a 720p stream that is not playing on the nvidea shield in the livingroom
# ->
#in_resolutions=("720")
#ex_clients=("Livingroom Shield")

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
#note the current channel amount the media is playing
current_channels=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).audio_channels')
#note the librarySectionID of the media library
lib_key=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/library/metadata/$rating_key?X-Plex-Token=$main_plex_token" | jq -rM .MediaContainer.Metadata[].librarySectionID)
#note the path to the media file
file_path=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).file')

#0.1 disable exclusion rules when inclusion rules are set
#and
#0.2 check if the stream follows the inclusion rules; if not, exit
if [[ -n "${in_library_source_ids[@]}" ]]
then
	unset ex_library_source_ids
	if ! [[ " ${in_library_source_ids[@]} " =~ "$lib_key" ]]
	then
		echo "Media does not fall under inclusion rules; ignoring"
		exit 0
	fi
fi
if [[ -n "${in_library_target_ids[@]}" ]]
then
	unset ex_library_target_ids
fi
if [[ -n "${in_library_remote_target_ids[@]}" ]]
then
	unset ex_library_remote_target_ids
fi
if [[ -n "${in_media_rating_keys[@]}" ]]
then
	unset ex_media_rating_keys
	if ! [[ " ${in_media_rating_keys[@]} " =~ "$rating_key" ]]
	then
		echo "Media does not fall under inclusion rules; ignoring"
		exit 0
	fi
fi
if [[ -n "${in_resolutions[@]}" ]]
then
	unset ex_resolutions
	if ! [[ " ${in_resolutions[@]} " =~ "$current_res" ]]
	then
		echo "Media does not fall under inclusion rules; ignoring"
		exit 0
	fi
fi
if [[ -n "${in_channels[@]}" ]]
then
	unset ex_channels
	if ! [[ " ${in_channels[@]} " =~ "$current_channels" ]]
	then
		echo "Media does not fall under inclusion rules; ignoring"
		exit 0
	fi
fi
if [[ -n "${audio_in_clients[@]}" ]]
then
	unset audio_ex_clients
	if ! [[ " ${audio_in_clients[@]} " =~ "$player" ]]
	then
		echo "Media does not fall under inclusion rules for audio; ignoring audio upgrade"
		audio_upgrading=false
	fi
fi
if [[ -n "${video_in_clients[@]}" ]]
then
	unset video_ex_clients
	if ! [[ " ${video_in_clients[@]} " =~ "$player" ]]
        then
                echo "Media does not fall under inclusion rules for video; ignoring video upgrade"
                video_upgrading=false
        fi
fi

#0.3 check if the stream falls under any exclusions; if so, exit
if [[ " ${ex_resolutions[@]} " =~ "$current_res" ]] \
|| [[ " ${ex_library_source_ids[@]} " =~ "$lib_key" ]] \
|| [[ " ${ex_media_rating_keys[@]} " =~ "$rating_key" ]] \
|| [[ " ${ex_channels[@]} " =~ "$current_channels" ]]
then
	echo "Media falls under exclusion rules; ignoring"
	exit 0
fi
if [[ " ${audio_ex_clients[@]} " =~ "$player" ]]
then
	echo "Media falls under exclusion rules for audio; ignoring audio upgrade"
	audio_upgrading=false
fi
if [[ " ${video_ex_clients[@]} " =~ "$player" ]]
then
	echo "Media falls under exclusion rules for video; ignoring video upgrade"
	video_upgrading=false
fi


if [[ "$audio_upgrading" = true ]]
then
#1.1 check if theres a higher audio channel track available
movie_output=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/library/metadata/$rating_key?X-Plex-Token=$main_plex_token")
mapfile -t avail_channels < <(echo "$movie_output" | jq -rM --arg FILE "$file_path" '.MediaContainer.Metadata[].Media[].Part[] | select(.file==$FILE).Stream[] | select(.streamType==2).channels')
mapfile -t avail_id < <(echo "$movie_output" | jq -rM --arg FILE "$file_path" '.MediaContainer.Metadata[].Media[].Part[] | select(.file==$FILE).Stream[] | select(.streamType==2).id')
for level in "${!avail_channels[@]}"
do
	if [[ "${avail_channels[$level]}" -gt "$current_channels" ]]
	then
		#an audio track with a higher channel count was found
		echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.setAudioStream(audioStreamID='${avail_id[$level]}', mtype='video')" | python3 -
	fi
done
fi

if [[ "$video_upgrading" = true ]]
then
#2.1 check if theres a better version available in the same library ("Play version")
movie_output=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/library/metadata/$rating_key?X-Plex-Token=$main_plex_token")
mapfile -t avail_res < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
mapfile -t avail_id < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].id)
for level in "${!avail_res[@]}"
do
	avail_res[$level]=$(echo "${avail_res[$level]}" | sed -e "s|k$|000|" -e "s|p$||")
	if [[ "${res_lad[${avail_res[$level]}]}" -lt "${res_lad[$current_res]}" ]]
	then
		#same library but higher version was found (better "Play version")
		view_offset=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).view_offset')
		section_id=$(echo "$movie_output" | jq .MediaContainer.Metadata[].librarySectionID)
		offset_media_id="$(($(echo "$movie_output" | jq '.MediaContainer.Metadata[].Media[].id' | grep -nPo "^\d+$" | grep -Po "^\d+(?=.*${avail_id[$level]})")-1))"
		#stop the current stream
		echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.stop(mtype='video')" | python3 -
		#start the stream on the same client but now playing the higher version
                echo "Starting stream from main server"
                echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID($section_id).get('$(echo "$full_title" | sed "s|'|\\'|g")')
client = plex.client(\"$player\")
client.playMedia(movie, offset=$view_offset, key=\"$key\", mediaIndex=\"$offset_media_id\")" | python3 -
		exit 0
	fi
done

#2.2 check if theres a better version in another library.
mapfile -t alternate_lib_keys < <(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port/search?X-Plex-Token=$main_plex_token&query=$(echo "$full_title" | sed "s| |%20|g")" | jq -rM --arg "LIBKEY" "$lib_key" --arg "GUID" "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID) | select(.librarySectionID!=$LIBKEY).key')
for level in "${alternate_lib_keys[@]}"
do
	movie_output=$(curl -sL -H 'Accept: application/json' "http://$main_plex_ip:$main_plex_port$level?X-Plex-Token=$main_plex_token")
	if [[ " ${ex_library_target_ids[@]} " =~ "$(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].librarySectionID)" ]]
	then
		continue
	fi
	if ! [[ " ${in_library_target_ids[@]} " =~ "$(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].librarySectionID)" ]] \
	&& [[ -n "${in_library_target_ids[@]}" ]]
	then
		continue
	fi
	mapfile -t avail_res < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
	mapfile -t avail_id < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].id)
	for level_2 in "${!avail_res[@]}"
	do
		avail_res[$level_2]=$(echo "${avail_res[$level_2]}" | sed -e "s|k$|000|" -e "s|p$||")
		if [[ "${res_lad[${avail_res[$level_2]}]}" -lt "${res_lad[$current_res]}" ]]
		then
			#different library but higher version was found
			key="$level"
			view_offset=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).view_offset')
			section_id=$(echo "$movie_output" | jq .MediaContainer.Metadata[].librarySectionID)
			offset_media_id="$(($(echo "$movie_output" | jq '.MediaContainer.Metadata[].Media[].id' | grep -nPo "^\d+$" | grep -Po "^\d+(?=.*${avail_id[$level_2]})")-1))"
			#stop the current stream
			echo "Stopping current stream from main server"
			echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.stop(mtype='video')" | python3 -
			#start the stream on the same client but now playing the higher version from a different library
			echo "Starting stream from main server"
			echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID($section_id).get('$(echo "$full_title" | sed "s|'|\\'|g")')
client = plex.client(\"$player\")
client.playMedia(movie, offset=$view_offset, key=\"$key\", mediaIndex=\"$offset_media_id\")" | python3 -
			exit 0
		fi
	done
done

#2.3 check if theres a better version on the backup server if setup
if [[ -n "$backup_plex_ip" ]] \
&& [[ -n "$backup_plex_port" ]] \
&& [[ -n "$backup_plex_token" ]]
then
	mapfile -t alternate_lib_keys < <(curl -sL -H 'Accept: application/json' "http://$backup_plex_ip:$backup_plex_port/search?X-Plex-Token=$backup_plex_token&query=$(echo "$full_title" | sed "s| |%20|g")" | jq -rM --arg "LIBKEY" "$lib_key" --arg "GUID" "$guid" '.MediaContainer.Metadata[] | select(.guid==$GUID) | select(.librarySectionID!=$LIBKEY).key')
	for level in "${alternate_lib_keys[@]}"
	do
		movie_output=$(curl -sL -H 'Accept: application/json' "http://$backup_plex_ip:$backup_plex_port$level?X-Plex-Token=$backup_plex_token")
		if [[ " ${ex_library_remote_target_ids[@]} " =~ "$(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].librarySectionID)" ]]
		then
			continue
		fi
		if ! [[ " ${in_library_remote_target_ids[@]} " =~ "$(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].librarySectionID)" ]] \
        	&& [[ -n "${in_library_remote_target_ids[@]}" ]]
        	then
        	        continue
        	fi
		mapfile -t avail_res < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].videoResolution)
		mapfile -t avail_id < <(echo "$movie_output" | jq -rM .MediaContainer.Metadata[].Media[].id)
		for level_2 in "${!avail_res[@]}"
		do
			avail_res[$level_2]=$(echo "${avail_res[$level_2]}" | sed -e "s|k$|000|" -e "s|p$||")
		    	if [[ "${res_lad[${avail_res[$level_2]}]}" -lt "${res_lad[$current_res]}" ]]
		    	then
	        		#different server but higher version was found
		        	key="$level"
			    	view_offset=$(curl -sL "http://$main_tautulli_ip:$main_tautulli_port/api/v2?apikey=$main_tautulli_token&cmd=get_activity" | jq -rM --arg ID "$session_id" '.response.data.sessions[] | select(.session_id==$ID).view_offset')
		        	section_id=$(echo "$movie_output" | jq .MediaContainer.Metadata[].librarySectionID)
				offset_media_id="$(($(echo "$movie_output" | jq '.MediaContainer.Metadata[].Media[].id' | grep -nPo "^\d+$" | grep -Po "^\d+(?=.*${avail_id[$level_2]})")-1))"
			    	#stop the current stream
			    	echo "Stopping current stream from main server"
			    	echo "from plexapi.server import PlexServer
baseurl = 'http://$main_plex_ip:$main_plex_port'
token = '$main_plex_token'
plex = PlexServer(baseurl, token)

client = plex.client(\"$player\")
client.stop(mtype='video')" | python3 -
		    		#start the stream on the same client but now playing the higher version from a different server
		    		echo "Starting stream from backup server"
		    		echo "from plexapi.server import PlexServer
baseurl = 'http://$backup_plex_ip:$backup_plex_port'
token = '$backup_plex_token'
plex = PlexServer(baseurl, token)

movie = plex.library.sectionByID($section_id).get('$(echo "$full_title" | sed "s|'|\\'|g")')
client = plex.client(\"$player\")
client.playMedia(movie, offset=$view_offset, key=\"$key\", mediaIndex=\"$offset_media_id\")" | python3 -
			        exit 0
		    	fi
		done
	done
fi
fi

exit 0
