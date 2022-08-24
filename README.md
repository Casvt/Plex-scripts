# Plex-scripts

This repository is a collection of scripts that I made targeted at applications like Plex, the arr's and Tautulli. It is inspired by the JBOPS repo. The scripts were made after requests, made by other people, in [this](https://www.reddit.com/r/PleX/comments/pbwf41/ill_make_any_script_suggestions_you_give/) reddit post. The target of most scripts is to expand the functionality of the applications. These scripts often fulfill a request for a feature made by many users of the applications a long time ago.

Info about the use case of every script can be found at the top inside the file. Info about how to setup the scripts can be found in the [wiki](https://github.com/Casvt/Plex-scripts/wiki/Setup). Eventhough it all started with making requests using comments under a reddit post, now we make requests using [GitHub issues](https://github.com/Casvt/Plex-scripts/issues) for which you can find info [here](https://github.com/Casvt/Plex-scripts/wiki/Requesting).

## Favourites
A few of my personal favourites:
1. [audio_sub_changer.py](https://github.com/Casvt/Plex-scripts/blob/main/changing_settings/audio_sub_changer.py): change audio/subtitle streams based on desired language for an episode, season, series, movie or complete library
2. [plex_sync.py](https://github.com/Casvt/Plex-scripts/blob/main/multiple_servers/plex_sync.py), keep two plex instances synced where you can sync collections, posters (e.g. custom posters set for media), intro markers, watch history and playlists. You can select, for the last two, which users you want to sync it for as those are user specific.
3. [stream_upgrader.py](https://github.com/Casvt/Plex-scripts/blob/main/stream_control/stream_upgrader.py): upgrade the stream's video (resolution) or audio (channel count) when there is a better one available wherever it may be (e.g. you start streaming a 1080p movie but you have a 4k version in a different library so the script will change the stream to that version).
4. [plex_exporter_importer.py](https://github.com/Casvt/Plex-scripts/blob/main/multiple_servers/plex_exporter_importer.py): export metadata of plex media and save it in one big database file. Then you can do the reverse with importing, where the databasefile is read and the values are applied to the plex item. This way you can "carry" custom metadata between plex servers (supporting metadata, advanced metadata, watched status, posters, arts (backgrounds), collections, intro markers, chapter thumbnails and server settings).
5. [advanced_playlists.py](https://github.com/Casvt/Plex-scripts/blob/main/playlist_collection/advanced_playlists.py): create playlists containing (multiple) series in custom orders like shuffled, semi-shuffled (series sequential but episodes shuffled) and staggered.

## Great scripts, but why?
I've noticed that plex, the arr's and tautulli all are great applications but they have their flaws. Often, people say "Plex is great, but..." or "Sonarr is cool but I hate that...". Now ofcourse software can't be perfect for everyone as everyone want's to do something different, but the amount of but's that these applications have is a little too much.

I have quite a bit of experience, working with these applications and thus I thought "why not help out?" I know their api's well, what is possible and not, etc. So I started the reddit thread found above where people could tell their but's and I would fix them in the form of a script. This repository is the result of that post (and a few scripts made after my own but's). I just want everyone to enjoy these great applications to their fullest. It's also great practise for me as I'm learning new languages and this ofcourse helps me getting comfortable in them.

## BASH
There are a few scripts in the repository that are written in BASH. I'm slowly converting all those scripts to python scripts.

## Donations
I don't accept money. I'm literally 16. You can "pay" me by sharing the repository with other people.

### **Browse around and take a look! Happy "but's"-removing**
