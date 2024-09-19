#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    When an episode is downloaded and imported in sonarr, unmonitor that episode.

Setup:
    1. Fill the variables below.
    2. Go to the Sonarr web-UI -> Settings -> Connect -> + -> Custom Script:
        Name = whatever you want
        Triggers = 'On Import' and 'On Upgrade'
        Tags = whatever if needed
        path = /path/to/unmonitor_downloaded_episodes.py
"""

from json import dumps, loads
from os import getenv
from urllib.request import Request, urlopen

# ===== FILL THESE VARIABLES =====
sonarr_base_url = ''
sonarr_api_token = ''
# ================================

# Environmental Variables
sonarr_base_url = getenv('sonarr_base_url', sonarr_base_url)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
base_url = sonarr_base_url.rstrip('/')


def _get_api_version() -> str:
    """Fetch the api version

    Returns:
        str: The api version. E.g. 'v3'.
    """
    with urlopen(f'{base_url}/api?apikey={sonarr_api_token}') as resp:
        api_version: str = loads(resp.read().decode('utf-8'))["current"]
    return api_version


def unmonitor_downloaded_episodes(
    episode_id: str,
    api_version: str = 'v3'
) -> bool:
    """Unmonitor an episode based on it's Sonarr ID.

    Args:
        episode_id (str): The ID of the episode to unmonitor.

        api_version (str, optional): The API version of the Sonarr instance.
            Defaults to 'v3'.

    Returns:
        bool: Whether or not there was a network error.
    """
    data = {
        'episodeIds': [episode_id],
        'monitored': False
    }
    send_data = dumps(data)

    req = Request(
        url=f"{base_url}/api/{api_version}/episode/monitor?apikey={sonarr_api_token}",
        data=send_data.encode("utf-8"),
        headers={
            'Content-Type': 'application/json; charset=UTF-8'},
        method="PUT")

    with urlopen(req) as resp:
        return resp.getcode() < 400


if __name__ == '__main__':
    # Handle testing of the script by sonarr
    if getenv('sonarr_eventtype') == 'Test':
        if not sonarr_base_url or not sonarr_api_token:
            print('Error: Not all variables are set')
            exit(1)

        _get_api_version()

        exit(0)

    episode_id = str(getenv('sonarr_episodefile_id'))

    unmonitor_downloaded_episodes(episode_id, _get_api_version())
