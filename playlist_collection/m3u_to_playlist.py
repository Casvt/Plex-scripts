#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Convert a .m3u file to a plex playlist.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 m3u_to_playlist.py -h
        or
        python m3u_to_playlist.py -h

Note:
    Getting this to work is a bit hard. The feature is not even available in the
    Plex web-UI. It is unclear why it sometimes works and sometimes doesn't.
    Tips:
        1. Supply a path that Plex can directly access. So the file has to be
            accessible directly by the Plex server.

        2. Supply an absolute path, not a relative path.

        3. Make sure the m3u file is complete, uses absolute filepaths as much
            as possible, and has the essential metadata.

        4. All files mentioned in the m3u file must be available in Plex and be
            in the given library.

Examples:
    --File "/media/music/playlists/favourite_music.m3u" --LibraryName "Music"

        Create a playlist from the "Music" library using the file
        "/media/music/playlists/favourite_music.m3u".

    --File "/media/music/playlists/toms_music.m3u" --LibraryName "Music" --User "Tom"

        Create a playlist for the user "Tom" from the "Music" library using the
        file "/media/music/playlists/toms_music.m3u".
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


def _gather_user_tokens(
    ssn: 'Session',
    users: List[str] = ['@me']) -> List[str]:
    """Get api tokens based on user list.

    Args:
        ssn (Session): The plex requests session to fetch with.
        users (List[str], optional): The list of users to get the tokens of.
            Defaults to ['@me'].

    Returns:
        List[str]: The list of tokens.
    """
    machine_id = ssn.get(
        f'{base_url}/'
    ).json()['MediaContainer']['machineIdentifier']
    shared_users = ssn.get(
        f'http://plex.tv/api/servers/{machine_id}/shared_servers'
    ).text
    user_data = dict(map(
        lambda r: r.split('"')[0:7:6],
        shared_users.split('username="')[1:]
    ))
    user_data['@me'] = plex_api_token
    if '@all' not in users:
        return [v for k, v in user_data.items() if k in users]
    else:
        return list(user_data.values())


def m3u_to_playlist(
    ssn: 'Session',
    library_name: str,
    file_path: str,
    users: List[str] = ['@me']
) -> List[int]:
    """Convert a .m3u file to a plex playlist.

    Args:
        ssn (Session): The plex requests session to fetch with.

        library_name (str): The name of the target library.

        file_path (str): The path to the m3u file.

        users (List[str], optional): The list of users to create the playlist
        for.
            Defaults to ['@me'].

    Raises:
        ValueError: Library not found.

    Returns:
        List[int]: List of rating keys of the playlists created.
    """
    tokens = _gather_user_tokens(ssn, users)

    sections = ssn.get(
        f'{base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])

    for lib in sections:
        if lib['title'] == library_name:
            break
    else:
        raise ValueError("Library not found")

    result_json = [
        int(ssn.post(
            f'{base_url}/playlists/upload',
            params={
                'sectionID': lib['key'],
                'path': file_path,
                'X-Plex-Token': user_token
            }
        ).json()['MediaContainer']['Metadata'][0]['ratingKey'])
        for user_token in tokens
    ]
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
    parser = ArgumentParser(description="Convert a .m3u file to a plex playlist.")
    parser.add_argument('-l', '--LibraryName', type=str, required=True, help="Name of target library")
    parser.add_argument('-f', '--File', type=str, required=True, help="File path to the .m3u file")
    parser.add_argument('-u', '--User', type=str, action='append', default=['@me'], help="Select the user(s) to apply this script to; Give username, '@me' for yourself or '@all' for everyone; allowed to give argument multiple times")
    # autopep8: on

    args = parser.parse_args()

    try:
        m3u_to_playlist(
            ssn,
            args.LibraryName, args.File,
            args.User
        )

    except ValueError as e:
        parser.error(e.args[0])
