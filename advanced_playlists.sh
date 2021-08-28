#!/bin/bash

#The use case of this script is the following:
#	Make a playlist with the desired series in it and most importantly, in the order that you want:
#	Randomize/sort, stagger, etc.

#IMPORTANT: The playlist will be added to the users playlists that the apikey is of.
#IMPORTANT: This script is only made for shows, not for movies or music.

#ip address of the plex server
plex_ip=xxx.xxx.xxx.xxx
#port of the plex server
plex_port=xxxxx
#api token of the user that has access to the server; the playlist will be added to this user
plex_api_token=xxxxxxxxxxetc.

#--------------------------------------------

if ! [[ "$plex_port" =~ ^[0-9]{1,5}$ ]]
then
	echo "Error: $level is not a valid port"
	exit 1
fi

if ! [[ "$plex_port" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
	echo "Error: $level is not a valid ip-address"
	exit 1
fi

if ! [[ "$plex_api_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
	echo "Error: $level is not a valid plex token"
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

#Select the series to be added to the playlist
unset series_selection
unset include_specials
until [[ ${series_selection,,} = continue ]] \
&& [[ -n ${selected_series_keys[@]} ]] \
|| [[ ${series_selection,,} = cancel ]]
do
	clear
	echo "Selected series (will be shown in the order you add them):"
	for level in "${selected_series_title[@]}"
	do
		echo "$level"
	done
	unset series_selection
	until [[ ${series_selection,,} =~ ^(cancel|search|remove|continue)$ ]]
	do
		read -rp "cancel | continue | remove | search: " series_selection
	done
	if [[ "${series_selection,,}" = search ]]
	then
		unset series_search
		until [[ -n $series_search ]]
		do
			read -rp "cancel | Give search term for series: " series_search
		done
		if [[ ${series_search,,} = cancel ]]
		then
			:

		else
			search_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/search?X-Plex-Token=$plex_api_token&query=$(echo "$series_search" | sed "s| |%20|g")" 2>/dev/null | jq -rM '.MediaContainer.Metadata[] | select(.type=="show")' 2>/dev/null)
			mapfile -t series_title < <(echo "$search_output" | jq -rM .title)
			mapfile -t series_year < <(echo "$search_output" | jq -rM .year)
			mapfile -t series_key < <(echo "$search_output" | jq -rM .ratingKey)
			for level in "${!series_title[@]}"
			do
				if ! [[ " ${selected_series_title[@]} " =~ "${series_title[$level]}" ]]
				then
					echo "$((level+1))^|^${series_title[$level]} (${series_year[$level]})"
				else
					printf "\033[1;31m$((level+1))^|^${series_title[$level]} (${series_year[$level]})\033[0m"
				fi
			done | column -tes "^"
			if [[ -n ${series_title[@]} ]]
			then
			unset search_selection
			until [[ $search_selection -ge 1 ]] \
			&& [[ $search_selection -le ${#series_title[@]} ]] \
			&& [[ ! " ${selected_series_title[@]} " =~ "${series_title[$((search_selection-1))]}" ]] \
			|| [[ ${search_selection,,} = cancel ]]
			do
				read -rp "cancel | Choose series to add to the collection (1/${#series_title[@]}): " search_selection
			done
			if [[ ${search_selection,,} = cancel ]]
			then
				:

			elif [[ $search_selection -ge 1 ]] \
			&& [[ $search_selection -le ${#series_title[@]} ]]
			then
				selected_series_title=("${selected_series_title[@]}" "${series_title[$((search_selection-1))]}")
				selected_series_keys=("${selected_series_keys[@]}" "${series_key[$((search_selection-1))]}")
			fi
			fi
		fi

	elif [[ "${series_selection,,}" = remove ]] \
	&& [[ -n ${selected_series_title[@]} ]]
	then
		clear
		for level in "${!selected_series_title[@]}"
		do
			echo "$((level+1))^|^${selected_series_title[$level]}"
		done | column -tes "^"
		unset remove_selection
		until [[ "$remove_selection" -ge 1 ]] \
		&& [[ "$remove_selection" -le ${#selected_series_title[@]} ]] \
		|| [[ "${remove_selection,,}" = cancel ]]
		do
			read -rp "cancel | Choose series to remove from the list (1/${#selected_series_title[@]}): " remove_selection
		done
		if [[ "${remove_selection,,}" = cancel ]]
		then
			:

		elif [[ $remove_selection -ge 1 ]] \
		&& [[ "$remove_selection" -le ${#selected_series_title[@]} ]]
		then
			removed_title="${selected_series_title[$((remove_selection-1))]}"
			removed_key="${selected_series_keys[$((remove_selection-1))]}"
			mapfile -t selected_series_title < <(for loop in "${selected_series_title[@]}"; do echo "$loop"; done | grep -v "^$removed_title$")
			mapfile -t selected_series_keys < <(for loop in "${selected_series_keys[@]}"; do echo "$loop"; done | grep -v "^$removed_key$")
		fi

	elif [[ "${series_selection,,}" = continue ]]
	then
		unset special_selection
		until [[ "${special_selection,,}" =~ ^(y|n|yes|no|cancel)$ ]]
		do
			read -rp "cancel | Include season 0 (specials) in the playlist (y|n)? " special_selection
		done
		if [[ "${special_selection,,}" = cancel ]]
		then
			unset series_selection

		elif [[ "${special_selection,,}" =~ ^(y|yes)$ ]]
		then
			include_specials=true

		elif [[ "${special_selection,,}" =~ ^(n|no)$ ]]
		then
			include_specials=false
		fi

	elif [[ "${series_selection,,}" = cancel ]]
	then
		exit 0
	fi
done

echo "Making files to hold orders in"
#we store the orders of the episodes in files:
#series by series order
for level in "${!selected_series_keys[@]}"
do
	echo "${selected_series_title[$level]} - /library/metadata/$level/children"
	case "$include_specials" in
	false ) mapfile -t season_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/${selected_series_keys[$level]}/children?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Metadata[] | select(.index!=0).ratingKey') ;;
	true ) mapfile -t season_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/${selected_series_keys[$level]}/children?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Metadata[].ratingKey') ;;
	esac
	for level_2 in "${season_keys[@]}"
	do
		season_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/$level_2/children?X-Plex-Token=$plex_api_token")
		season_number=$(echo "$season_output" | jq .MediaContainer.Metadata[].parentIndex | head -n 1)
		echo "	Season $season_number - /library/metadata/$level_2/children"
		mapfile -t episode_number < <(echo "$season_output" | jq -rM .MediaContainer.Metadata[].index)
		mapfile -t episode_keys < <(echo "$season_output" | jq -rM .MediaContainer.Metadata[].ratingKey)
		for level_3 in "${!episode_number[@]}"
		do
			key_info["${episode_keys[$level_3]}"]="${selected_series_title[$level]} - S$season_number E${episode_number[$level_3]} - /library/metadata/${episode_keys[$level_3]}"
			echo "		${key_info[${episode_keys[$level_3]}]}"
			echo "${episode_keys[$level_3]}" >> series_series_playlist.txt
		done
	done
done

#complete shuffle order
shuf series_series_playlist.txt > full_shuffle_playlist.txt

#play series sequentially but stagger the shows
for level in $(seq 0 "$((${#selected_series_keys[@]}-1))")
do
	unset temp_series
	case "$include_specials" in
	false ) mapfile -t season_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/${selected_series_keys[$level]}/children?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Metadata[] | select(.index!=0).ratingKey') ;;
	true ) mapfile -t season_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/${selected_series_keys[$level]}/children?X-Plex-Token=$plex_api_token" | jq -rM '.MediaContainer.Metadata[].ratingKey') ;;
	esac
	for level_2 in "${season_keys[@]}"
	do
		mapfile -t episode_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/metadata/$level_2/children?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.Metadata[].ratingKey)
		temp_series=("${temp_series[@]}" "${episode_keys[@]}")
	done
	echo "${temp_series[@]}" | sed -E "s| |\n|g" > series$((level+1))_keys
	echo "${selected_series_title[level]}'s keys:"
	cat series$((level+1))_keys | tr "\n" " "
	echo ""
done

for level in $(seq 1 $(for level in $(seq 1 "${#selected_series_keys[@]}"); do wc -l < series$level\_keys; done | sort -n | tail -n 1))
do
	for level_2 in $(seq 1 "${#selected_series_keys[@]}")
	do
		if [[ "$level" -le $(wc -l < series$level_2\_keys) ]]
		then
			head -n $level < series$level_2\_keys | tail -n 1 >> seq_stag_playlist.txt
		fi
	done
done

#series shuffle order
ls -A1 | grep -Po "^series\d+_keys" | \
while read -r level
do
	shuf "$level" >> series_shuffle_playlist.txt
	rm "$level"
done

#done making order files
echo "Making of files completed"
sleep 1,5s

#select layout of playlist
preset=s_by_s
unset season_selection
until [[ "${season_selection,,}" = continue ]]
do
	clear
	echo "Setup the order:"
	case "$preset" in
	s_by_s )
		cat series_series_playlist.txt | \
		while read -r level
		do
			echo "${key_info[$level]}"
		done
		;;
	comp_shuf )
		cat full_shuffle_playlist.txt | \
		while read -r level
		do
			echo "${key_info[$level]}"
		done
		;;
	seq_stag )
		cat seq_stag_playlist.txt | \
		while read -r level
		do
			echo "${key_info[$level]}"
		done
		;;
	ser_shuf )
		cat series_shuffle_playlist.txt | \
		while read -r level
		do
			echo "${key_info[$level]}"
		done
	esac
	unset season_selection
	until [[ "${season_selection,,}" =~ ^(cancel|presets|continue)$ ]]
	do
		read -rp "cancel | continue | presets: " season_selection
	done
	if [[ "${season_selection,,}" = cancel ]]
	then
		exit 0

	elif [[ "${season_selection,,}" = presets ]]
	then
		preset_amount=5
		echo "1 | custom - COMING IN V2!"
		echo "  |	Decide on a per-episode basis what should be shown,"
		echo "  |	which episode's to statically show (6th episode in the season will be show as the sixth video)"
		echo "  |	and which episode's to shuffle (contained per season or complete series shuffle)."
		echo "2 | play series sequentially but stagger the shows"
		echo "  |	Series 1 - Ep 1"
		echo "  |	Series 2 - Ep 1"
		echo "  |	Series 1 - Ep 2"
		echo "  |	Series 2 - Ep 2"
		echo "  |	Series 1 - Ep 3"
		echo "  |	Series 2 - Ep 3"
		echo "  |	Etc."
		echo "3 | complete shuffle"
		echo "  |	Randomize every episode of every season of every series."
		echo "  |	Basically everything through each other in random order."
		echo "4 | series shuffle"
		echo "  |	Play the series sequentially, but within the series the episodes are shuffled"
		echo "5 | series by series"
		echo "  |	play the entirity of Series 1, then Series 2, etc."
		unset preset_selection
		until [[ $preset_selection -ge 2 ]] \
		&& [[ $preset_selection -le $preset_amount ]] \
		|| [[ "${preset_selection,,}" = cancel ]]
		do
			read -rp "cancel | Choose preset number (1/$preset_amount): " preset_selection
		done
		case "${preset_selection,,}" in
			1 ) preset=custom ;;
			2 ) preset=seq_stag ;;
			3 ) preset=comp_shuf ;;
			4 ) preset=ser_shuf ;;
			5 ) preset=s_by_s ;;
		esac

	elif [[ "${season_selection,,}" = continue ]]
	then
		if [[ "$preset" != s_by_s ]]
		then
			rm series_series_playlist.txt
		fi
		if [[ "$preset" != comp_shuf ]]
		then
			rm full_shuffle_playlist.txt
		fi
		if [[ "$preset" != seq_stag ]]
		then
			rm seq_stag_playlist.txt
		fi
		if [[ "$preset" != ser_shuf ]]
		then
			rm series_shuffle_playlist.txt
		fi
		case "$preset" in
		s_by_s ) mv series_series_playlist.txt final_playlist.txt ;;
		comp_shuf ) mv full_shuffle_playlist.txt final_playlist.txt ;;
		seq_stag ) mv seq_stag_playlist.txt final_playlist.txt ;;
		ser_shuf ) mv series_shuffle_playlist.txt final_playlist.txt ;;
		esac
		unset playlist_title
		until [[ -n $playlist_title ]]
		do
			read -rp "Give the name for the playlist: " playlist_title
		done
		machine_id=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.machineIdentifier)
		curl -sL -X POST "http://$plex_ip:$plex_port/playlists?type=video&title=$(echo "$playlist_title" | sed "s| |%20|g")&smart=0&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/$(tr "\n" "," < final_playlist.txt | sed "s|,$|\n|")&X-Plex-Token=$plex_api_token"
		rm final_playlist.txt
		exit 0
	fi
done
