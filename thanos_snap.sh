#!/bin/bash

#The use case of this script is the following:
#   When you're watching Avengers: Infinity War, at the moment that thanos snaps, this script will be launched.
#   When the script is launched, there is a 50/50 chance that your data directory will be deleted
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
#   Conditions:
#       Condition {1} = Progress Duration (sec) is 7866
#       Condition {2} = Title is Avengers: Infinity War
#       Condition Logic = {1} and {2}
#SAVE
#
#WARNING: THERE'S A 50/50 CHANCE THAT YOU'LL LOOSE YOUR COMPLETE DATA DIRECTORY. THAT INCLUDES POSTERS, METADATA, COLLECTIONS, ETC.
#         I AM NOT RESPONSIBLE FOR ANY LOSS OF IMPORTANT DATA

plex_data_dir="/var/lib/plexmediaserver/Library/Application Suport/Plex Media Server/"

if (( RANDOM % 2 ))
then
    rm -R "$plex_data_dir"
else
    echo "It's your lucky day."
fi
exit 0