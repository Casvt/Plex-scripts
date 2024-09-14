#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    When a movie is downloaded and imported in radarr, unmonitor that movie.

Setup:
    1. Fill the variables below.
    2. Go to the Radarr web-UI -> Settings -> Connect -> + -> Custom Script:
        Name = whatever you want
        Triggers = 'On Import' and 'On Upgrade'
        Tags = whatever if needed
        path = /path/to/unmonitor_downloaded_movies.py
"""

from json import dumps, loads
from os import getenv
from urllib.request import Request, urlopen

# ===== FILL THESE VARIABLES =====
radarr_base_url = ''
radarr_api_token = ''
# ================================

# Environmental Variables
radarr_base_url = getenv('radarr_base_url', radarr_base_url)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)
base_url = radarr_base_url.rstrip('/')


def _get_api_version() -> str:
    """Fetch the api version

    Returns:
        str: The api version. E.g. 'v3'.
    """
    with urlopen(f'{base_url}/api?apikey={radarr_api_token}') as resp:
        api_version: str = loads(resp.read().decode('utf-8'))["current"]
    return api_version


def unmonitor_downloaded_movies(
    movie_id: str,
    api_version: str = 'v3'
) -> bool:
    """Unmonitor a movie based on it's Radarr ID.

    Args:
        movie_id (str): The ID of the movie to unmonitor.

        api_version (str, optional): The API version of the Radarr instance.
            Defaults to 'v3'.

    Returns:
        bool: Whether or not there was a network error.
    """
    data = {
        'movieIds': [movie_id],
        'monitored': False
    }
    send_data = dumps(data)

    req = Request(
        url=f"{base_url}/api/{api_version}/movie/editor?apikey={radarr_api_token}",
        data=send_data.encode("utf-8"),
        headers={
            'Content-Type': 'application/json; charset=UTF-8'},
        method="PUT")

    with urlopen(req) as resp:
        return resp.getcode() < 400


if __name__ == '__main__':
    # Handle testing of the script by radarr
    if getenv('radarr_eventtype') == 'Test':
        if not radarr_base_url or not radarr_api_token:
            print('Error: Not all variables are set')
            exit(1)

        _get_api_version()

        exit(0)

    movie_id = str(getenv('radarr_movie_id'))

    unmonitor_downloaded_movies(movie_id, _get_api_version())
