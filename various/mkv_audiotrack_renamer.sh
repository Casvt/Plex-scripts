#!/bin/bash

#The use case of this script is the following:
#	If the name of an audio track follows the regex '.*\d+(\.\d)?(\.\d)?$',
#	rename that track to '[codec] [channel layout]'
#	E.G. 'Surround 7.1' -> 'Dolby Digital 7.1'
#	The script does this for every mkv file in the folder given below (also recursively)

movie_folder=/home/cas/plex-media/Movies/

#--------------------------------------------

if ! [[ -d "$movie_folder" ]]
then
	echo "Error: movie folder is not a valid folder"
	exit 1
fi

if apt-cache policy mkvtoolnix | grep -Pq "^\s*Installed: \(none\)$"
then
	echo "Error: mkvtoolnix is not installed"
	exit 1
fi

#-----

grep -R ".*.mkv" "$movie_folder" | grep -Po "^Binary file \K.*(?= matches$)" | \
while read -r level
do
	unset tracks
	mkv_info=$(mkvinfo "$level")
	mapfile -t audio_tracks < <(echo "$mkv_info" | grep -Poz 'Track UID: \K\d+(?=.*\n.  \+ Track type: audio)' | tr '\0' '\n')
	for level_2 in "${audio_tracks[@]}"
	do
		if [[ -z $(echo "$mkv_info" | grep -Poz "$level_2(.*\n)+?.*Name: .*?\K\d{1,2}(\.\d{1,2})?(\.\d{1,2})?" | tr '\0' '\n') ]]
		then
			continue
		fi
		tracks=("${tracks[@]}" "--edit track:=$level_2 --set name=$(echo "$mkv_info" | grep -Poz "$level_2(.*\n)+?.*Codec ID: A_\K.*" | tr '\0' '\n')_$(echo "$mkv_info" | grep -Poz "$level_2(.*\n)+?.*Name: .*?\K\d{1,2}(\.\d{1,2})?(\.\d{1,2})?" | tr '\0' '\n')")
	done
	echo "$level"
	echo "${tracks[@]}"
	mkvpropedit "$level" ${tracks[@]} 2>/dev/null
	echo ""
	sleep 1s
done
