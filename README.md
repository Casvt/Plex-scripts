# Plex-scripts

This repository is a collection of scripts that I made targeted at applications like Plex, the arr's and Tautulli. It is inspired by the JBOPS repo. The scripts were made after requests, made by other people, in [this](https://www.reddit.com/r/PleX/comments/pbwf41/ill_make_any_script_suggestions_you_give/) reddit post. The target of most scripts is to expand the functionality of the applications. The scripts often fulfill requests for a feature made by many users of the applications a long time ago.

Info about the use case of every script can be found at the top inside the file.

## Setup
1. First of all, download the script onto your computer.
2. Inside the file, fill the required variables. More info about this can be found below.
3. Some scripts just need to be run manually, but others need to be setup in sonarr/radarr/tautulli or need to be run at an interval (like 5 min or 12 hours). Instructions on how to run the script can be found inside the file.

### Variables
Inside the scripts, there are variables that you need to fill in order for the script to work. These variables are named after the value that they should have. They all follow the same logic: `[software]_[requested value]`. So if the variable is called `sonarr_port`, the value should be the port that sonarr is running on (default is 8989). It will look like this: 
```python
sonarr_port = '8989'
```

Examples of variables and their expected values:
```python
plex_ip = '192.168.2.15'
sonarr_ip = '192.168.2.15'
radarr_ip = '192.168.2.15'
#when there is a base url added (e.g. in sonarr or radarr), append it to the ip:
sonarr_ip = '192.168.2.15/sonarr'

plex_port = '32400'
sonarr_port = '8989'
radarr_port = '7878'

plex_api_token = 'abcdefghijklmnopqrst'
sonarr_api_token = 'abcdefghijklmnopqrstuvwxyz'
radarr_api_token = 'abcdefghijklmnopqrstuvwxyz'
```
The api token of sonarr or radarr can be found in the web-ui under Settings -> General -> Security -> API Key

To find the plex api token:
1. Find where the data directory of plex is located for your OS [here](https://support.plex.tv/articles/202915258-where-is-the-plex-media-server-data-directory-located/)
2. Open the file `Preferences.xml` inside the data directory found in step 1
3. Find the value of `PlexOnlineToken` (e.g. `PlexOnlineToken="abcdefghijklmnopqrst"` -> `abcdefghijklmnopqrst`)
4. Enter it as the value for `plex_api_token` (as seen above)

## Favourites
A few of my personal favourites:
1. [audio_sub_changer.py](https://github.com/Casvt/Plex-scripts/blob/main/changing_settings/audio_sub_changer.py): change audio/subtitle streams based on desired language for an episode, season, series, movie or complete library
2. [plex_sync.py](https://github.com/Casvt/Plex-scripts/blob/main/multiple_servers/plex_sync.py), keep two plex instances synced where you can sync collections, posters (e.g. custom posters set for media), watch history and playlists. You can select, for the last two, which users you want to sync it for as those are user specific.
3. [stream_upgrader.py](https://github.com/Casvt/Plex-scripts/blob/main/stream_control/stream_upgrader.py): upgrade the stream's video (resolution) or audio (channel count) when there is a better one available wherever it may be (e.g. you start streaming a 1080p movie but you have a 4k version in a different library so the script will change the stream to that version).

## Great scripts, but why?
I've noticed that plex, the arr's and tautulli all are great applications but they have their flaws. Often, people say "Plex is great, but..." or "Sonarr is cool but I hate that...". Now ofcourse software can't be perfect for everyone as everyone want's to do something different, but the amount of but's that these applications have is a little too much. I have quite a bit of experience, working with these applications and thus I thought "why not help out?" I know their api's well, what is possible and not, etc. So I started the reddit thread found above where people could tell their but's and I would fix them in the form of a script. This repository is the result of that post (and a few scripts made after my own but's). I just want everyone to enjoy these great applications to their fullest. It's also great practise for me as I'm learning new languages and this ofcourse helps me getting comfortable in them.

## Other repo's
I'm not the only one with a repository for scripts regarding these softwares. Check these out too:
- [JBOPS (Just a bunch of plex scripts)](https://github.com/blacktwin/JBOPS)
- [Tautulli scripts](https://github.com/Tautulli/Tautulli/wiki/Custom-Scripts#list-of-user-created-scripts)

## Feature requests
Before making a feature request, check here if someone hasn't made a better version of one of my scripts:
- intro_skipper.py -> [mdhiggins's version](https://github.com/mdhiggins/PlexAutoSkip)

Otherwise, make a feature request in the [discord server](https://discord.gg/AbCQ9tduZA) or make a github issue and just tell me what you would like to see being added. Or if you already did it yourself, feel free to make a pull request.

## BASH
There are a few scripts in the repository that are written in BASH. I'm slowly converting all those scripts to python scripts.

## Donations
I don't accept money. I'm literally 16. You can "pay" me by sharing the repository with other people.

### **Browse around and take a look! Happy "but's"-removing**
