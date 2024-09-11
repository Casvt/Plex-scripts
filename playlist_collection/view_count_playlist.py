#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Remove entries in a playlist when they've met or surpassed the given viewcount.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 view_count_playlist.py -h
        or
        python view_count_playlist.py -h
    3. Run this script at an interval to keep the collection updated.
        Decide for yourself what the interval is (e.g. every 12h).

Examples:
    --PlaylistName "My Playlist" --ViewCount "5"

        Remove all entries in the playlist "My Playlist" that have been watched
        5 or more times.

    -p "Trash Playlist" -c "0"

        Remove all entries from the playlist "Trash Playlist".
"""

from os import getenv
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from requests import Session

# ===== FILL THESE VARIABLES =====
plex_base_url = ''
plex_api_token = ''
# ================================

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = plex_base_url.rstrip('/')


def view_count_playlist(
    ssn: 'Session',
    playlist_name: str,
    view_count: int
) -> List[int]:
    """Remove entries in a playlist when they've met or surpassed the given viewcount.

    Args:
        ssn (Session): The plex requests session to fetch with.
        playlist_name (str): The name of the playlist to process.
        view_count (int): The view count that is the minimum to be removed.

    Raises:
        ValueError: Playlist not found.

    Returns:
        List[int]: List of media rating keys that were removed.
    """
    result_json = []

    playlists: List[dict] = ssn.get(
        f'{base_url}/playlists'
    ).json()['MediaContainer'].get('Metadata', [])

    for playlist in playlists:
        if playlist['title'] != playlist_name:
            continue
        break
    else:
        raise ValueError("Playlist not found")

    # Playlist found
    playlist_entries: List[dict] = ssn.get(
        f'{base_url}/playlists/{playlist["ratingKey"]}/items'
    ).json()['MediaContainer'].get('Metadata', [])

    for entry in playlist_entries:
        if int(entry.get('viewCount', 0)) >= view_count:
            # Entry surpassed view count so remove it
            result_json.append(int(entry['ratingKey']))
            ssn.delete(
                f'{base_url}/playlists/{playlist["ratingKey"]}/items/{entry["playlistItemID"]}'
            )

    return result_json


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Remove entries in a playlist when they've met or surpassed the given viewcount.")
    parser.add_argument('-p', '--PlaylistName', type=str, required=True, help="Name of target playlist")
    parser.add_argument('-c', '--ViewCount', type=int, required=True, help="The viewcount that is the minimum to be removed")
    # autopep8: on

    args = parser.parse_args()

    try:
        view_count_playlist(ssn, args.PlaylistName, args.ViewCount)

    except ValueError as e:
        parser.error(e.args[0])
