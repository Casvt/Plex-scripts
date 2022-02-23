# Plex-scripts

This repository is a collection of scripts that I made targeted at applications like Plex, the arr's and Tautulli. It is inspired by the JBOPS repo. The scripts were made after requests, made by other people, in [this](https://www.reddit.com/r/PleX/comments/pbwf41/ill_make_any_script_suggestions_you_give/) reddit post. The target of most scripts is to expand the functionality of the applications. The scripts often fulfill requests for a feature made by many users of the applications a long time ago.

Info about the use case of every script can be found at the top inside the file.

## I've found a script that I like, but how do I set it up?
1. First of all, download the script onto your computer.
2. Inside the file, fill the required variables. These variables are at the top and the name of the variable describes what the value should be.
3. Some scripts just need to be run manually, some need to be setup in sonarr/radarr/tautulli and some need to be run at an interval (like 5 min or 12 hours). Instructions on how to run the script can be found inside the file.

## I haven't found a script that I like, so any suggestions?
A few of my person favorites:
1. [audio_sub_changer.py](https://github.com/Casvt/Plex-scripts/blob/main/changing_settings/audio_sub_changer.py), change audio/subtitle streams based on desired language for an episode, season, series, movie or complete library
2. [plex_sync.py](https://github.com/Casvt/Plex-scripts/blob/main/multiple_servers/plex_sync.py), keep two plex instances synced where you can sync collections, posters (e.g. custom posters set for media), watch history and playlists. You can select, for the last two, which users you want to sync it for as those are user specific.
3. [intro_skipper.py](https://github.com/Casvt/Plex-scripts/blob/main/stream_control/intro_skipper.py), skip the intro/outro/advertisement in media when it is marked as such with chapters or markers
4. [stream_upgrader.py](https://github.com/Casvt/Plex-scripts/blob/main/stream_control/stream_upgrader.py), upgrade the stream's video (resolution) or audio (channel count) when there is a better one available wherever it may be (e.g. you start streaming a 1080p movie but you have a 4k version in a different library so the script will change the stream to that version).

## Great scripts, but why?
I've noticed that plex, the arr's and tautulli all are great applications but they have their flaws. Often, people say "Plex is great, but..." or "Sonarr is cool but I hate that...". Now ofcourse software can't be perfect for everyone as everyone want's to do something different, but the amount of but's that these applications have is a little too much. I have quite a bit of experience, working with these applications and thus I thought "why not help out?" I know their api's well, what is possible and not, etc. So I started the reddit thread found above where people could tell their but's and I would fix them in the form of a script. This repository is the result of that post (and a few scripts made after my own but's). I just want everyone to enjoy these great applications to their fullest. It's also great practise for me as I'm learning new languages and this ofcourse helps me getting comfortable in them.

## Heartwarming story but what if I don't like your scripts?
Then you can check out these repo's:
- [JBOPS (Just a bunch of plex scripts)](https://github.com/blacktwin/JBOPS)
- [Tautulli scripts](https://github.com/Tautulli/Tautulli/wiki/Custom-Scripts#list-of-user-created-scripts)

## What if I want more features in your scripts?
First of all check here if someone hasn't made a better version of one of my scripts:
- intro_skipper.py -> [mdhiggins's version](https://github.com/mdhiggins/PlexAutoSkip)

Otherwise, make a feature request in the [discord server](https://discord.gg/AbCQ9tduZA) or make a github issue and just tell me what you would like to be added. Or if you already did it yourself, feel free to make a pull request.

## I don't like BASH
Yes I know. I'm slowly converting all bash scripts to python scripts.

## You're such an amazing person, I want to sent you money!
I don't accept money. I'm literally 16. You can "pay" me by sharing the repo with other people.

### **Browse around and take a look! Happy "but's"-removing**
