#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Sync a playlist from one user to one or more other users.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 push_playlist.py -h
        or
        python push_playlist.py -h

Examples:
    --SourceUser "User1" --PlaylistName "Favourite Movies" --TargetUser "User2"

        Push User1's playlist "Favourite Movies" to User2.

    --SourceUser "Batman" --PlaylistName "Villians" --TargetUser "Robin" --TargetUser "Butler"

        Push Batman's playlist "Villains" to Robin and Butler.

    --SourceUser "Admin" --PlaylistName "New Media" --TargetUser "@all"

        Push Admin's playlist "New Media" to all users on the server.
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


def push_playlist(
    ssn: 'Session',
    source_user: str,
    target_users: List[str],
    playlist_name: str
) -> List[int]:
    """Sync a playlist from one user to one or more other users.

    Args:
        ssn (Session): The plex requests session to fetch with.

        source_user (str): Username of the source user; @me to target yourself.

        target_users (List[str]): Usernames of the target users;
            @me to target yourself, @all to target everyone.

        playlist_name (str): The name of the playlist to push.

    Raises:
        ValueError: No target users selected.
        ValueError: Source user also as target user selected.
        ValueError: Source user can't be '@all'.
        ValueError: Source user not found.
        ValueError: No target users found.
        ValueError: Source playlist not found.
        ValueError: Source playlist is empty.

    Returns:
        List[int]: List of media rating keys that were in the source playlist.
    """
    # Check for illegal arg parsing
    if not target_users:
        raise ValueError("No target users selected")
    if source_user in target_users:
        raise ValueError("Source user also as target user selected")
    if source_user == '@all':
        raise ValueError("Source user can't be '@all'")

    # Gather tokens
    source_token = _gather_user_tokens(ssn, [source_user])
    if not source_token:
        raise ValueError("Source user not found")
    source_token = source_token[0]

    target_tokens = _gather_user_tokens(ssn, target_users)
    if not target_tokens:
        raise ValueError("No target users found")

    # Find source playlist
    playlists = ssn.get(
        f'{base_url}/playlists',
        params={'X-Plex-Token': source_token}
    ).json()['MediaContainer'].get('Metadata', [])

    for source_playlist in playlists:
        if source_playlist['title'] == playlist_name:
            break
    else:
        raise ValueError("Source playlist not found")

    # Get content of source playlist
    playlist_content = ssn.get(
        f'{base_url}/playlists/{source_playlist["ratingKey"]}/items',
        params={'X-Plex-Token': source_token}
    ).json()['MediaContainer'].get('Metadata', [])

    playlist_ratingkeys = [int(i['ratingKey']) for i in playlist_content]
    if not playlist_ratingkeys:
        raise ValueError("Source playlist is empty")

    # Create playlists
    machine_id = ssn.get(
        f'{base_url}/'
    ).json()['MediaContainer']['machineIdentifier']

    for target_token in target_tokens:
        # Delete old playlist if it's there
        user_playlists = ssn.get(
            f'{base_url}/playlists',
            params={'X-Plex-Token': target_token}
        ).json()['MediaContainer'].get('Metadata', [])

        for user_playlist in user_playlists:
            if user_playlist['title'] == playlist_name:
                ssn.delete(
                    f'{base_url}/playlists/{user_playlist["ratingKey"]}',
                    params={'X-Plex-Token': target_token}
                )

        # Create playlist for target user
        new_ratingkey = ssn.post(
            f'{base_url}/playlists',
            params={
                'X-Plex-Token': target_token,
                'title': source_playlist['title'],
                'smart': '0',
                'type': source_playlist['playlistType'],
                'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(str(r) for r in playlist_ratingkeys)}'
            }
        ).json()['MediaContainer']['Metadata'][0]['ratingKey']

        if 'thumb' in source_playlist:
            # Upload poster
            ssn.post(
                f'{base_url}/playlists/{new_ratingkey}/posters',
                params={
                    'X-Plex-Token': target_token,
                    'url': f'{base_url}{source_playlist["thumb"]}?X-Plex-Token={source_token}'})

    return playlist_ratingkeys


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Sync a playlist from one user to one or more other users.")
    parser.add_argument('-s', '--SourceUser', type=str, required=True, help="Username of the source user; @me to target yourself")
    parser.add_argument('-p', '--PlaylistName', type=str, required=True, help="The name of the playlist to push")
    parser.add_argument('-t', '--TargetUser', type=str, action='append', required=True, help="Select the user(s) to target; Give username, '@me' for yourself or '@all' for everyone; allowed to give argument multiple times")
    # autopep8: on

    args = parser.parse_args()

    try:
        push_playlist(
            ssn,
            args.SourceUser,
            args.TargetUser,
            args.PlaylistName
        )

    except ValueError as e:
        parser.error(e.args[0])
