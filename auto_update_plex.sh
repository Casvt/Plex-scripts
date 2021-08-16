#!/bin/bash

#ip of plex server to auto update
ipplexserver=XXX.XXX.XXX.XXX
#port of that plex server
plexport=XXXXX
#api token of that plex server
plexapitoken=XXXXXXXXXXXetc.
#directory where the logfile should go
logfolder=/home/cas/scripts/logs

#--------------------------------------------

if ! [[ $(id -u) = 0 ]]
then
	echo "Error: script needs to be run as root"
	exit 1
fi

for level in curl jq wget
do
	if apt-cache policy $level | grep -Pq "^\s*Installed: \(none\)$"
	then
		echo "Error: $level is not installed"
		exit 1
	fi
done

if ! [[ "$ipplexserver" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
then
	echo "Error: invalid ip-address given as value for \$ipplexserver"
	exit 1
fi

if ! [[ "$plexport" =~ ^[0-9]{1,5}$ ]]
then
	echo "Error: invalid port given as value for \$plexport"
	exit 1
fi

if ! [[ "$plexapitoken" =~ ^([a-zA-Z0-9]|_|-|~){19,21}$ ]]
then
	echo "Error: invalid api-token given as value for \$plexapitoken"
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

#find out the current version of the server
currentversion=$(curl -sL "http://$ipplexserver:$plexport/servers?X-Plex-Token=$plexapitoken" | grep -Po "address=\"$ipplexserver\" port=\"$plexport\" \S+ version=\"\K[a-z\d\.-]+" | head -n 1)
#find the newest downloadlink
#IMPORTANT: CHANGE THE JQ PATH TO LEAD TO THE LINK THAT FITS YOUR OS/DISTRO
#IT IS CURRENTLY SET TO UBUNTU 64BIT
newlink=$(curl -sL https://plex.tv/pms/downloads/5.json | jq -rM '.computer.Linux.releases[] | select(.build=="linux-x86_64") | select(.distro=="debian").url')
#extract the newest version from the newest link
newversion=$(echo "$newlink" | sed "s|/|\n|g" | head -n 5 | tail -n 1)

#if versions don't match, update.
if ! [[ "$currentversion" = "$newversion" ]]
then
	#new version available
	#if someone is watching, check every 10mintues if it has ended. if so, then continue
	until [[ ! $(curl -sL http://$ipplexserver:$plexport/status/sessions?X-Plex-Token=$plexapitoken | grep "</Video>") ]]
	do
		echo "$(date '+%d/%m/%Y %H:%M:%S') | Someone is streaming; checking again in 10 minutes" >> "$logfolder/auto_update_plex.log"
		sleep 10m
	done
	#download new version
	wget -q "$newlink"
	if [[ $? = 0 ]]
	then
		#download suceeded
		echo "$(date '+%d/%m/%Y %H:%M:%S') | Downloaded new version" >> "$logfolder/auto_update_plex.log"
		#stop plex
		sudo systemctl stop plexmediaserver.service
		echo "$(date '+%d/%m/%Y %H:%M:%S') | Stopped plexmediaserver.service" >> "$logfolder/auto_update_plex.log"
		#install update
		sudo dpkg -i plexmediaserver*.deb 1>/dev/null 2>"$logfolder/auto_update_plex.log"
		if [[ $? = 0 ]]
		then
			#install suceeded
			echo "$(date '+%d/%m/%Y %H:%M:%S') | Installed new version" >> "$logfolder/auto_update_plex.log"

		else
			#can't install new version
			echo "$(date '+%d/%m/%Y %H:%M:%S') | Failed to install new version" >> "$logfolder/auto_update_plex.log"
		fi
		#start plex
		sudo systemctl start plexmediaserver.service
		echo "$(date '+%d/%m/%Y %H:%M:%S') | Started plexmediaserver.service" >> "$logfolder/auto_update_plex.log"
		#remove update file
		rm plexmediaserver*.deb 2>/dev/null
		rm plexmediaserver*.deb* 2>/dev/null

	else
		#can't download new version
		echo "$(date '+%d/%m/%Y %H:%M:%S') | Failed to download new version" >> "$logfolder/auto_update_plex.log"
	fi

else
	#no new version available
	echo "$(date '+%d/%m/%Y %H:%M:%S') | No new version" >> "$logfolder/auto_update_plex.log"
fi
