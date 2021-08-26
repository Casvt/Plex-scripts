#!/bin/bash

#https://www.reddit.com/r/PleX/comments/pbwf41/ill_make_any_script_suggestions_you_give/

movie_folder=/home/cas/Share

grep -R ".*.mkv" "$movie_folder" | grep -Po "^Binary file \K.*(?= matches$)" | \
while read -r level
do
	unset tracks
	mapfile -t track_type < <(mkvinfo "$level" | grep -Poz "\| \+ Track\n(.*\n)+?.*Track type: \K\w" | tr "\0" "\n" | sort -u)
	for level_2 in ${!track_type[@]}
	do
		tracks=("${tracks[@]}" "--edit track:${track_type[$level_2]}1 --delete name")
	done
	echo "$level"
	echo "${tracks[@]}"
	mkvpropedit "$level" --tags all: -d prev-filename -d next-filename -d prev-uid -d next-uid ${tracks[@]}
	echo ""
	sleep 1s
done
