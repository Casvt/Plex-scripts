#! /bin/bash

#ip adress of radarr instance
radarr_ip=XXX.XXX.XXX.XXX
#port radarr instance is running on
radarr_port=XXX
#api token of radarr instance
radarr_api_token=XXXXXXXXXXXXXXXXXetc.
#directory where the logfile should go
logfolder=/home/cas/scripts/logs

#--------------------------------------------

for level in curl jq mkvtoolnix
do
	if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
	then
		echo "Error: $level is not installed"
		exit 1
	fi

done

if ! [[ "$radarr_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
	echo "Error: invalid ip-address given as value for \$radarr_ip"
        exit 1
fi

if ! [[ "$radarr_port" =~ ^[0-9]{1,5}$ ]]
then
        echo "Error: invalid port given as value for \$radarr_port"
	exit 1
fi

if ! [[ "$radarr_api_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
        echo "Error: invalid api-token given as value for \$radarr_api_token"
        exit 1
fi

if ! [[ -d "$logfolder" ]]
then
        echo "Error: the folder to store the logfile in doesn't exist"
        exit 1
else
        logfolder=$(echo "$logfolder" | sed "s|/$||")
fi

#-------

#store the api output for all the movies in a variable, because with alot of movies it takes alot of time to process and puts load on your system
movie_output=$(curl -sL "http://$radarr_ip:$radarr_port/api/v3/movie?apikey=$radarr_api_token" -H "accept: application/json")
#collect the paths to all movie files that are mkv and have multiple languages from which one is english
mapfile -t path < <(echo "$movie_output" | jq -rM '.[] | select(.hasFile==true).movieFile | select(.languages!=[{"id": 1, "name": "English"}]) | . as $parent | .languages[] | select(.name=="English") | $parent.path' | grep "\.mkv$")
#the rest will be done one-by-one for each file
for level in "${path[@]}"
do
	#$level contains paths to movie files that have multiple audio tracks from which, atleast one english is
	#removing all audio tracks that aren't english or dutch
	#check what languages the file has now (e.g. "English\nHindi\nItalian")
	track_lang=$(echo "$movie_output" | jq -rM --arg LEVEL "$level" '.[] | .movieFile | select(.path==$LEVEL).languages[] | .name')
	#grab the id of every audio track
	track_ids=$(mkvmerge -i "$level" | grep -Po "^Track ID \K\d*(?=: audio)")
	#this variable will contain info about which tracks to keep (e.g. keep "the first track" and "the third")
	keep_track=$(seq 1 $(echo "$track_lang" | wc -l) | grep -o "$(echo "$track_lang" | grep -n "English\|Dutch" | grep -Po "^\d*")")
	#get the track ids of "the first track" and "the third track"
	keep_track_ids=$(echo "$keep_track" | while read -r level_2; do echo "$track_ids" | head -n $level_2 | tail -n 1; done | paste -sd",")
	#inform that we've found a file with too much audiotracks and that we have started to make the cleaner version
	echo "Starting to make copy of file with audiotracks removed: $level" >> "$logfolder/audiotrack_filter.log"
	#making a copy of the file but with cleaned audiotracks
	mkvmerge -o "$(echo "$level" | sed "s|\.mkv$|_temp\.mkv|")" --audio-tracks "$keep_track_ids" "$level" 1>/dev/null
	if [[ $? = 0 ]]
	then
		#successfully made copy with cleaned audiotracks
		echo "Finished making copy" >> "$logfolder/audiotrack_filter.log"
		#remove original file
		rm "$level"
		if [[ $? = 0 ]]
		then
			#successfully removed original file
			echo "Removed old file" >> "$logfolder/audiotrack_filter.log"
			#rename the new file with the original name (after this, it will look like we repleaced the file)
			mv "$(echo "$level" | sed "s|\.mkv$|_temp\.mkv|")" "$level" \
			&& echo "Renamed new file" >> "$logfolder/audiotrack_filter.log" \
			|| echo "Failed to rename new file" >> "$logfolder/audiotrack_filter.log"
			#updating radarr (radarr won't see the changes made to the file, so we have to manually update the api to remove all the unneccecery languages)
			put_object=$(curl -sL "http://$radarr_ip:$radarr_port/api/v3/movie?apikey=$radarr_api_token" | jq --arg PATH "$level" '.[].movieFile | select(.path==$PATH) | {"indexerFlags":.indexerFlags,"languages":.languages,"movieFileIds":[.id],"quality":.quality,"releaseGroup":.releaseGroup} | .languages[] |= select(.name=="English" or .name=="Dutch")')
			curl -sL -X PUT \
			-d "$put_object" \
			"http://$radarr_ip:$radarr_port/api/v3/movieFile/editor?apikey=$radarr_api_token" 1>/dev/null \
			&& echo "Updated Radarr" >> "$logfolder/audiotrack_filter.log" \
			|| echo "Failed to update Radarr" >> "$logfolder/audiotrack_filter.log"

		else
			#failed to remove original file
			echo "Failed to remove old file" >> "$logfolder/audiotrack_filter.log"
		fi

	else
		#mkvmerge failed to make copy with cleaned audiotracks
		echo "Failed making copy" >> "$logfolder/audiotrack_filter.log"
	fi
done

exit 0
