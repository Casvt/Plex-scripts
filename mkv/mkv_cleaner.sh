#!/bin/bash

#made after this suggestion
#https://www.reddit.com/r/PleX/comments/pbwf41/ill_make_any_script_suggestions_you_give/haf05od/?utm_source=share&utm_medium=web2x&context=3

#The use case of this script is the following:
#	It will remove all unnecessary metadata in a .mkv file
#SETUP:
#	Enter the folder where all the files are located below and run the script (it is recursive so it's okay to have every file in a sepperate folder).
#	The idea is that you run this every 12 or 24 hours using crontab for example.

movie_folder=/home/cas/plex-media/Movies

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
	mapfile -t track_type < <(mkvinfo "$level" | grep -Poz "\| \+ Track\n(.*\n)+?.*Track type: \K\w" | tr "\0" "\n" | sort -u)
	for level_2 in ${!track_type[@]}
	do
		tracks=("${tracks[@]}" "--edit track:${track_type[$level_2]}1 --delete name")
	done
	echo "$level"
	mkvpropedit "$level" --tags all: -d prev-filename -d next-filename -d prev-uid -d next-uid ${tracks[@]}
	echo ""
done
