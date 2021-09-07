#!/bin/bash

#The use case of this script is the following:
#	After selecting a library and giving a quality profile (e.g. main 10),
#	list all movies/episodes that match that profile.

#ip address of plex server
plex_ip=xxx.xxx.xxx.xxx
#port of plex server
plex_port=xxxxx
#api token of plex server
plex_api_token=xxxxxxxxxetc.

#--------------------------------------------

if ! [[ "$plex_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
        echo "Error: not a valid ip"
        exit 1
fi

if ! [[ "$plex_port" =~ ^[0-9]{1,5}$ ]]
then
        echo "Error: not a valid port"
        exit 1
fi

if ! [[ "$plex_api_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
        echo "Error: not a valid api token"
        exit 1
fi

for level in curl jq
do
        if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
        then
                echo "Error: $level is not installed"
                exit 1
        fi
done

#-----

script_kill()
{
	kill "$FIRSTPID"
	kill "$SECONDPID"
	kill "$THIRDPID"
	cat second_output
	cat third_output
	rm second_output third_output
	exit 0
}

mapfile -t lib_names < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Directory[] | select(.type=="movie" or .type=="show").title')
mapfile -t lib_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Directory[] | select(.type=="movie" or .type=="show").key')
for level in "${!lib_names[@]}"
do
	echo "$((level+1))^|^${lib_names[$level]}"
done | column -tes "^"
unset library_selection
until [[ "$library_selection" -ge 1 ]] \
&& [[ "$library_selection" -le "${#lib_names[@]}" ]] \
|| [[ "${library_selection,,}" = cancel ]]
do
	read -rp "cancel | Select a library (1/${#lib_names[@]}): " library_selection
done
if [[ "${library_selection,,}" = cancel ]]
then
	exit 0

elif [[ "$library_selection" -ge 1 ]] \
&& [[ "$library_selection" -le "${#lib_names[@]}" ]]
then
	unset selected_profile
	until [[ -n "$selected_profile" ]]
	do
		read -rp "cancel | Give the name of the quality profile: " selected_profile
	done
	if [[ "${selected_profile,,}" = cancel ]]
	then
		exit 0
	fi
	lib_key="${lib_keys[$((library_selection-1))]}"
	library_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections/$lib_key/all?X-Plex-Token=$plex_api_token")
	mapfile -t keys < <(echo "$library_output" | jq -rM '.MediaContainer.Metadata[].key')
	case "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM --arg KEY "$lib_key" '.MediaContainer.Directory[] | select(.key==$KEY).type')" in
	'movie' )
		devided_numbers=$(echo "scale=0;${#keys[@]}/3" | bc)
		mapfile -t first_keys < <(echo "${keys[@]}" | sed "s| |\n|g" | head -n "$devided_numbers")
		mapfile -t second_keys < <(echo "${keys[@]}" | sed "s| |\n|g" | head -n "$((devided_numbers*2))" | tail -n "$devided_numbers")
		mapfile -t third_keys < <(echo "${keys[@]}" | sed "s| |\n|g" | head -n "$((devided_numbers*3))" | tail -n "$devided_numbers")
		for level in "${first_keys[@]}"
		do
			profile=$(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[].videoProfile' | head -n 1)
			if [[ "$profile" != "$selected_profile" ]]
			then
				continue
			fi
			title=$(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).title')
			echo "$profile - $title"
		done & FIRSTPID=$!
		for level in "${second_keys[@]}"
                do
                        profile=$(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[].videoProfile' | head -n 1)
                        if [[ "$profile" != "$selected_profile" ]]
                        then
				continue
                        fi
                        title=$(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).title')
                        echo "$profile - $title" >> second_output
                done & SECONDPID=$!
		for level in "${third_keys[@]}"
                do
                        profile=$(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[].videoProfile' | head -n 1)
                        if [[ "$profile" != "$selected_profile" ]]
                        then
				continue
                        fi
                        title=$(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).title')
                        echo "$profile - $title" >> third_output
                done & THIRDPID=$!
		trap script_kill SIGINT
		wait $FIRSTPID
		wait $SECONDPID
		wait $THIRDPID
		cat second_output
		cat third_output
		rm second_output third_output
		;;
	'show' )
		for level in "${keys[@]}"
		do
			#do this for every show in the library
			show_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port$level?X-Plex-Token=$plex_api_token")
			mapfile -t season_keys < <(echo "$show_output" | jq -rM .MediaContainer.Metadata[].key)
			series_title=$(echo "$show_output" | jq -rM '.MediaContainer.title2')
			for level_2 in "${season_keys[@]}"
			do
				#do this for every season of the show
				season_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port$level_2?X-Plex-Token=$plex_api_token")
				mapfile -t episode_keys < <(echo "$season_output" | jq -rM .MediaContainer.Metadata[].key)
				season_number=$(echo "$season_output" | jq .MediaContainer.Metadata[].parentIndex | head -n 1)
				for level_3 in "${episode_keys[@]}"
				do
					#do this for every episode of the season
					episode_number=$(echo "$season_output" | jq -rM --arg KEY "$level_3" '.MediaContainer.Metadata[] | select(.key==$KEY).index')
					profile=$(echo "$season_output" | jq -rM --arg KEY "$level_3" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[].videoProfile' | head -n 1)
					if [[ "$profile" != "$selected_profile" ]]
					then
						continue
					fi
					episode_title=$(echo "$season_output" | jq -rM --arg KEY "$level_3" '.MediaContainer.Metadata[] | select(.key==$KEY).title')
					echo "$profile - $series_title - S$season_number E$episode_number - $episode_title"
				done
			done
		done
		;;
	* )
		echo "Unsupported library type"
		exit 1
		;;
	esac
fi
