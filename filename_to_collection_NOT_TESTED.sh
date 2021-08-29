#! /bin/bash

#The use case of this script is the following:
#	If you have files in the format "Collection1.Collection2.Collection3.etc..mkv", the script will add the file to those collections
#	You can select/turn on/of collections to add the file to after adding the file
#	If there's a collection in the filename that doesn't exist (if you chose it; regarding the previous sentence), it will make it.

#ip address of the plex server
plex_ip=xxx.xxx.xxx.xxx
#port of the plex server
plex_port=xxxxx
#api token of the plex server (best is to copy it from the Preferences.xml file)
plex_api_token=xxxxxxxetc.
#select if you want to use the file browser or just supply the path.
use_browser=true #true/false
#set to true if you run on windows
windows=false #true/false

#--------------------------------------------

if [[ "$windows" = false ]]
then
	for level in curl jq
	do
		if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
		then
			echo "Error: $level is not installed"
			exit 1
		fi
	done
fi

if ! [[ "$plex_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
	echo "Error: invalid ip-address given as value for \$ipplexserver"
	exit 1
fi

if ! [[ "$plex_port" =~ ^[0-9]{1,5}$ ]]
then
	echo "Error: invalid port given as value for \$plexport"
	exit 1
fi

if ! [[ "$plex_api_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
	echo "Error: invalid api-token given as value for \$plexapitoken"
	exit 1
fi

#-----

machine_id=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.machineIdentifier)
mapfile -t lib_paths < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.Directory[].Location[].path)
mapfile -t lib_keys < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.Directory[].key)
for level in "${lib_keys[@]}"
do
	output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections/$level/collections?X-Plex-Token=$plex_api_token")
	lib_output=("${lib_output[@]}" "$output")
done

if [[ "$use_browser" = true ]]
then
	dir=/
	unset folder_selection
	until [[ "${folder_selection,,}" = cancel ]]
	do
	clear
	cd "$dir" || exit 1
	ls_output=$(ls -d */ 2>/dev/null | sed "s|/$||g")
	echo "--------------------------------"
	mapfile -t folders < <(echo "$ls_output")
	echo "$dir"
	for level in ${!folders[@]}
	do
		if [[ $level = 0 ]] \
		|| [[ -z ${folders[@]} ]]
		then
			echo "$level^|^.."
		fi
		if [[ -n ${folders[@]} ]]
		then
			echo "$((level+1))^|^${folders[$level]}"
		fi
		if [[ $level = $((${#folders[@]}-1)) ]] \
		&& [[ -n $ls_output ]]
		then
		    printf "\n\033[1;32m$((${#folders[@]}+1))^|^SELECT THIS FOLDER\033[0m\n"

		elif [[ $level = $((${#folders[@]}-1)) ]] \
		&& [[ -z $ls_output ]]
		then
		    printf "\n\033[1;32m${#folders[@]}^|^SELECT THIS FOLDER\033[0m\n"
		fi
	done | column -tes "^"
	echo "--------------------------------"
	if [[ -n $ls_output ]]
	then
	    read -rp "cancel | Choose directory (0/${#folders[@]}): " selected_dir
	else
	    read -rp "cancel | Choose directory (0): " selected_dir
	fi
	if [[ ${selected_dir,,} = cancel ]]
	then
		exit 0

	elif [[ $selected_dir -ge 0 ]] \
	&& [[ $selected_dir -lt ${#folders[@]} ]]
	then
	    if [[ $selected_dir = 0 ]]
	    then
	        dir=$(dirname "$dir")

	    elif [[ $selected_dir -ge 1 ]] \
	    && [[ $selected_dir -le ${#folders[@]} ]]
	    then
		case $dir in
		/ ) dir=/${folders[$((selected_dir-1))]} ;;
	        * ) dir=$dir/${folders[$((selected_dir-1))]} ;;
		esac
	    fi

	elif [[ $selected_dir = $((${#folders[@]}+1)) \
		&& -n $ls_output ]] \
	|| [[ $selected_dir = ${#folders[@]} \
		&& -z $ls_output ]]
	then
		folder_selection=cancel
		folder="$dir/"
	fi
	done
else
	unset folder_selection
	until [[ -d "$folder_selection" ]]
	do
		read -rp "cancel | Give path to folder: " folder_selection
	done
	if [[ "$folder_selection" =~ ".*(\\|/)$" ]]
	then
		folder="$folder_selection"
	else
		if [[ "$windows" = true ]]
		then
			folder="$folder_selection\\"
		else
			folder="$folder_selection/"
		fi
	fi
fi
mapfile -t files < <(ls -A1 "$folder" | grep -Po "(^|(\.|-))[A-Z0-9]([^\.]|[^-])+")

#---

for file in "${files[@]}"
do
	mapfile -t collections < <(echo "$file" | grep -Po "(^|(\.|-))\K.*?(?=(\.|-))")
	unset collection_selection
	until [[ "${collection_selection,,}" =~ ^(cancel|continue)$ ]]
	do
		echo "$folder$file"
		for collection in "${!collections[@]}"
		do
			if [[ " ${selected_collections[@]} " =~ "${collections[$collection]}" ]]
			then
				echo "$((collection+1))^|^${collections[$collection]}"
			else
				printf "\033[1;30m$((collection+1))^|^${collections[$collection]}\033[0m\n"
			fi
		done | column -tes "^"
		unset collection_selection
		until [[ "$collection_selection" -ge 1 \
			&& "$collection_selection" -le ${#collections[@]} ]] \
		|| [[ "${collection_selection,,}" = continue \
			&& -n "${selected_collections[@]}" ]] \
		|| [[ "${collection_selection,,}" = cancel ]]
		do
			read -rp "cancel | continue | Select collections to add this file to (1/${#collections[@]}): " collection_selection
		done
		if [[ "${collection_selection,,}" = cancel ]]
		then
			exit 0

		elif [[ $collection_selection -ge 1 ]] \
		&& [[ $collection_selection -le ${#collections[@]} ]]
		then
			if [[ " ${selected_collections[@]} " =~ "${collections[$((collection_selection-1))]}" ]]
			then
				selected_collections=("${selected_collections[@]/${collections[$((collection_selection-1))]}/}")
			else
				selected_collections=("${selected_collections[@]}" "${collections[$((collection_selection-1))]}")
			fi

		elif [[ "${collection_selection,,}" = continue ]] \
		&& [[ -n "${selected_collections[@]}" ]]
		then
			#do everything inside the loop for every selected collection
			for level in "${selected_collections[@]}"
			do
				#find the rating key of the collection; output is -n/-z $ratingkey of collection and $correct_lib_output is library output where collection was found
				unset ratingkey
				for level_2 in "${!lib_output[@]}"
				do
					ratingkey=$(echo "${lib_output[level_2]}" | jq -rM --arg TITLE "$level" '.MediaContainer.Metadata[] | select(.title==$TITLE).ratingKey' 2>/dev/null)
					if [[ -n "$ratingkey" ]] \
					&& [[ "$ratingkey" != null ]]
					then
						break
					fi
					unset ratingkey
				done
				#find the path of the library where the file is located in
				for path in "${lib_paths[@]}"
				do
					if [[ "$folder$file" =~ "$path" ]]
					then
						correct_path="$path"
						break
					else
						unset correct_path
					fi
				done
				#if the library was found where the file is located, continue; otherwise report
				if [[ -n "$correct_path" ]]
				then
					correct_lib_key=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM --arg PATH "$correct_path" '.MediaContainer.Directory[] | select(.Location[].path==$PATH).key')
					file_ratingkey=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections/$correct_lib_key/all?X-Plex-Token=$plex_api_token" | jq -rM --arg PATH "$folder$file" '.MediaContainer.Metadata[] | select(.Media[].Part[].file==$PATH).ratingKey')
					if [[ -n "$ratingkey" ]]
					then
						new_ratingkeys="$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/collections/$ratingkey/children" | jq -rM .MediaContainer.Metadata[].ratingKey | paste -sd,),$file_ratingkey"
						curl -sL -X PUT "http://$plex_ip:$plex_port/library/collections/$ratingkey/items?X-Plex-Token=$plex_api_token&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/$new_ratingkeys"
					else
						curl -sL -X POST "http://$plex_ip:$plex_port/library/collections?type=1&title=$(echo "$level" | sed "s| |%20|g")&smart=0&sectionId=$correct_lib_key&uri=server://$machine_id/com.plexapp.plugins.library/library/metadata/$file_ratingkey"
					fi
				else
					echo "Warning ($folder$file): The rootpath of the file didn't match up with one of the libraries. Skipping file"
				fi
			done
		fi
	done
done
