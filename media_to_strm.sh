#!/bin/bash

#The use case of this script will be the following:
#	A selected library will be scanned and for every movie/series,
#	there will be a file made with inside it the link to the highest resolution file,
#	keeping the folder structure.
#	The file will have the .strm extension, though you can easily change that.

#ip-address of the plex server
plex_ip=xxx.xxx.xxx.xxx
#port of the plex server
plex_port=xxxxx
#api token of the plex server
plex_api_token=xxxxxxxetc.
#should the url in the file be https or http?
#https = https://xxx-xxx-xxx-xxx.[machine_id].plex.direct:[port]/etc.
#http = http://xxx.xxx.xxx.xxx:[port]/etc.
https=false #true/false

#--------------------------------------------

for level in curl jq
do
	if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
	then
		echo "Error: $level is not installed"
		exit 1
	fi
done

if ! [[ "$plex_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
	echo "Error: invalid ip-address given as value for \$plex_ip"
	exit 1
fi

if ! [[ "$plex_port" =~ ^[0-9]{1,5}$ ]]
then
	echo "Error: invalid port given as value for \$plex_port"
	exit 1
fi

if ! [[ "$plex_api_token" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
	echo "Error: invalid api-token given as value for \$plex_api_token"
	exit 1
fi

if ! [[ "$https" =~ ^(true|false)$ ]]
then
	echo "Error: invalid boolean given as value for \$https"
	exit 1
fi

#-----

#set the resolution "ladder"
res_lad[8000]=1
res_lad[6000]=2
res_lad[4000]=3
res_lad[2000]=4
res_lad[1080]=5
res_lad[720]=6
res_lad[480]=7

machine_id=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.machineIdentifier)
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
	lib_key="${lib_keys[$((library_selection-1))]}"
	mapfile -t paths < <(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM --arg KEY "$lib_key" '.MediaContainer.Directory[] | select(.key==$KEY).Location[].path')
	unset destination_selection
	until [[ -d "$destination_selection" ]] \
	|| [[ "${destination_selection,,}" = cancel ]]
	do
		read -rp "cancel | Give path to folder where all the files will be put: " destination_selection
	done
	if [[ "${destination_selection,,}" = cancel ]]
	then
		exit 0

	elif [[ -d "$destination_selection" ]]
	then
		folder="$(echo "$destination_selection" | sed "s|/$||")"
		root_folder="$folder/${lib_names[$((library_selection-1))]}"
		mkdir "$root_folder"
		library_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections/$lib_key/all?X-Plex-Token=$plex_api_token")
		mapfile -t keys < <(echo "$library_output" | jq -rM '.MediaContainer.Metadata[].key')
		echo "$(echo "$library_output" | jq -rM '.MediaContainer.title1')"
		case "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port/library/sections?X-Plex-Token=$plex_api_token" | jq -rM --arg KEY "$lib_key" '.MediaContainer.Directory[] | select(.key==$KEY).type')" in
		"movie" )
			for level in "${keys[@]}"
			do
				#do this for every movie in the library
				mapfile -t media_path < <(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[].Part[].key')
				mapfile -t file_path < <(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[].Part[].file')
				echo "	$(echo "$library_output" | jq -rM --arg KEY "$level" '.MediaContainer.Metadata[] | select(.key==$KEY).title')"
				for level_2 in "${file_path[@]}"
				do
					file_res=("${file_res[@]}" "$(echo "$library_output" | jq -rM --arg KEY "$level" --arg FILE "$level_2" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[] | select(.Part[].file==$FILE).videoResolution' | sed "s|k$|000|")")
				done
				unset highest_res highest_path res_compare
				res_compare=100
				for level_2 in "${!file_res[@]}"
				do
					if [[ "${res_lad[${file_res[$level_2]}]}" -lt "$res_compare" ]]
					then
						res_compare="${res_lad[${file_res[$level_2]}]}"
						new_file_path="${file_path[$level_2]}"
						new_media_path="${media_path[$level_2]}"
					fi
				done
				file_path="$new_file_path"
				media_path="$new_media_path"
				unset reduced_file_path
				for level_2 in "${paths[@]}"
				do
					reduced_file_path="$(echo "$file_path" | sed "s|^$level_2/||")"
					if [[ "$reduced_file_path" != "$file_path" ]]
					then
						break
					fi
				done
				mkdir "$root_folder/$(dirname "$reduced_file_path")" 2>/dev/null
				filename=$(basename "$reduced_file_path")
				filename="${filename%.*}"
				if [[ "$https" = true ]]
				then
					echo "https://$(echo "$plex_ip" | sed "s|\.|-|g").$machine_id.plex.direct:$plex_port$media_path?download=0&X-Plex-Token=$plex_api_token" > "$root_folder/$(dirname "$reduced_file_path")/$filename.strm"
				else
					echo "http://$plex_ip:$plex_port$media_path?download=0&X-Plex-Token=$plex_api_token" > "$root_folder/$(dirname "$reduced_file_path")/$filename.strm"
				fi
			done
			;;
		"show" )
			for level in "${keys[@]}"
			do
				#do this for every show in the library
				show_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port$level?X-Plex-Token=$plex_api_token")
				mapfile -t season_keys < <(echo "$show_output" | jq -rM .MediaContainer.Metadata[].key)
				mkdir "$root_folder/$(basename "$(dirname "$(dirname "$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port${season_keys[0]}?X-Plex-Token=$plex_api_token" | jq -rM .MediaContainer.Metadata[].Media[].Part[].file | head -n 1)")")")" 2>/dev/null
				echo "	$(echo "$show_output" | jq -rM '.MediaContainer.title2')"
				for level_2 in "${season_keys[@]}"
				do
					#do this for every season of the show
					season_output=$(curl -sL -H 'Accept: application/json' "http://$plex_ip:$plex_port$level_2?X-Plex-Token=$plex_api_token")
					mapfile -t episode_keys < <(echo "$season_output" | jq -rM .MediaContainer.Metadata[].key)
					mkdir "$root_folder/$(basename "$(dirname "$(dirname "$(echo "$season_output" | jq -rM .MediaContainer.Metadata[].Media[].Part[].file | head -n 1)")")")/$(basename "$(dirname "$(echo "$season_output" | jq -rM .MediaContainer.Metadata[].Media[].Part[].file | head -n 1)")")"
					echo "		$(echo "$season_output" | jq -rM '.MediaContainer.title2')"
					for level_3 in "${episode_keys[@]}"
					do
						#do this for every episode of the season
						mapfile -t media_path < <(echo "$season_output" | jq -rM --arg KEY "$level_3" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[].Part[].key')
						mapfile -t file_path < <(echo "$season_output" | jq -rM --arg KEY "$level_3" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[].Part[].file')
						echo "			$(echo "$show_output" | jq -rM '.MediaContainer.title2') - S$(echo "$season_output" | jq -rM .MediaContainer.parentIndex)E$(echo "$season_output" | jq -rM --arg KEY "$level_3" '.MediaContainer.Metadata[] | select(.key==$KEY).index' | head -n 1) - $(echo "$season_output" | jq -rM --arg KEY "$level_3" '.MediaContainer.Metadata[] | select(.key==$KEY).title' | head -n 1)"
						for level_4 in "${file_path[@]}"
						do
							file_res=("${file_res[@]}" "$(echo "$season_output" | jq -rM --arg KEY "$level_3" --arg FILE "$level_4" '.MediaContainer.Metadata[] | select(.key==$KEY).Media[] | select(.Part[].file==$FILE).videoResolution' | sed "s|k$|000|")")
						done
						unset res_compare
						res_compare=100
						for level in "${!file_res[@]}"
						do
							if [[ "${res_lad[${file_res[$level]}]}" -lt "$res_compare" ]]
							then
								res_compare="${res_lad[${file_res[$level]}]}"
								new_file_path="${file_path[$level]}"
								new_media_path="${media_path[$level]}"
							fi
						done
						file_path="$new_file_path"
						media_path="$new_media_path"
						unset reduced_file_path
						for level_2 in "${paths[@]}"
						do
							reduced_file_path="$(echo "$file_path" | sed "s|^$level_2/||")"
							if [[ "$reduced_file_path" != "$file_path" ]]
							then
								break
							fi
						done
						filename=$(basename "$reduced_file_path")
						filename="${filename%.*}"
						if [[ "$https" = true ]]
						then
							echo "https://$(echo "$plex_ip" | sed "s|\.|-|g").$machine_id.plex.direct:$plex_port$media_path?download=0&X-Plex-Token=$plex_api_token" > "$root_folder/$(dirname "$reduced_file_path")/$filename.strm"
						else
							echo "http://$plex_ip:$plex_port$media_path?download=0&X-Plex-Token=$plex_api_token" > "$root_folder/$(dirname "$reduced_file_path")/$filename.strm"
						fi
					done
				done
			done
			;;
		"*" )
			echo "Error: unsuported library type"
			exit 1
			;;
		esac
	fi
fi
