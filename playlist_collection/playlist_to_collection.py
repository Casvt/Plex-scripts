#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Get the content of a playlist and put it in a collection.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 playlist_to_collection.py -h
        or
        python playlist_to_collection.py -h

Examples:
    --LibraryName "Films" --PlaylistName "Top Media"

        Put all movies from the playlist "Top Media" in a similarly named collection in the "Films" library.

    -l "Tv-series" -p "Top Media" -r

        Put all shows from the playlist "Top Media" in a similarly named collection in the "Tv-series" library.
        Remove the playlist afterwards.
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


TYPE_TO_ID = {
    'movie': '1',
    'show': '4',
    'artist': '10',
    'photo': '13'
}


def playlist_to_collection(
    ssn: 'Session',
    library_name: str,
    playlist_name: str,
    remove_playlist: bool = False
) -> List[int]:
    """Get the content of a playlist and put it in a collection.

    Args:
        ssn (Session): The plex requests session to fetch with.
        library_name (str): Name of library to put collection in.
        playlist_name (str): Name of playlist to get entries from.
        remove_playlist (bool, optional): Remove playlist afterwards.
            Defaults to False.

    Raises:
        ValueError: Playlist not found.
        ValueError: Library not found.
        ValueError: Library type not supported.
        ValueError: Playlist is empty.

    Returns:
        List[int]: List of media rating keys in playlist.
    """
    # Find playlist
    playlists: List[dict] = ssn.get(
        f'{base_url}/playlists'
    ).json()['MediaContainer'].get('Metadata', [])
    for playlist in playlists:
        if playlist['title'] == playlist_name:
            break
    else:
        raise ValueError("Playlist not found")

    # Find library
    sections = ssn.get(
        f'{base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])
    for lib in sections:
        if lib['title'] == library_name:
            break
    else:
        raise ValueError("Library not found")

    if not lib['type'] in TYPE_TO_ID:
        raise ValueError("Library type not supported")

    # Get playlist content
    playlist_entries = ssn.get(
        f'{base_url}/playlists/{playlist["ratingKey"]}/items'
    ).json()['MediaContainer'].get('Metadata', [])

    playlist_entries = [int(e['ratingKey']) for e in playlist_entries]
    if not playlist_entries:
        raise ValueError("Playlist is empty")

    # Remove already existing collection with same name
    collections = ssn.get(
        f'{base_url}/library/sections/{lib["key"]}/collections'
    ).json()['MediaContainer'].get('Metadata', [])
    for collection in collections:
        if collection['title'] == playlist_name:
            ssn.delete(
                f'{base_url}/library/collections/{collection["ratingKey"]}'
            )
            break

    # Create new collection
    machine_id = ssn.get(
        f'{base_url}/'
    ).json()['MediaContainer']['machineIdentifier']

    new_ratingkey = ssn.post(
        f'{base_url}/library/collections',
        params={
            'type': TYPE_TO_ID[lib['type']],
            'title': playlist_name,
            'smart': '0',
            'sectionId': lib['key'],
            'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join((str(e) for e in playlist_entries))}'
        }
    ).json()['MediaContainer']['Metadata'][0]['ratingKey']

    if 'thumb' in playlist:
        # Upload poster
        ssn.post(
            f'{base_url}/library/collections/{new_ratingkey}/posters',
            params={
                'url': f'{base_url}{playlist["thumb"]}?X-Plex-Token={plex_api_token}'})

    if remove_playlist:
        ssn.delete(f'{base_url}/playlists/{playlist["ratingKey"]}')

    return playlist_entries


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Get the content of a playlist and put it in a collection.")
    parser.add_argument('-l', '--LibraryName', type=str, required=True, help="Name of target library")
    parser.add_argument('-p', '--PlaylistName', type=str, required=True, help="Name of target playlist")
    parser.add_argument('-r', '--RemovePlaylist', action='store_true', help="Remove source playlist afterwards")
    # autopep8: on

    args = parser.parse_args()

    try:
        playlist_to_collection(
            ssn,
            args.LibraryName,
            args.PlaylistName,
            args.RemovePlaylist
        )

    except ValueError as e:
        parser.error(e.args[0])
