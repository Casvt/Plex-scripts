#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Make a playlist with the desired sersies in it and most importantly, in the
    order that you want: sequential, shuffled, semi-shuffled or staggered.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 advanced_playlists.py -h
        or
        python advanced_playlists.py -h

Examples:
    --Order "staggered" --Playlist Name "Short Shows" --SeriesName "1899" --SeriesName "The Billion Dollar Code" --SeriesName "Devs"

        Create a playlist called "Short Shows" containing the shows "1899",
        "The Billion Dollar Code" and "Devs". The episodes are ordered in a
        staggered way.
"""

from enum import Enum
from itertools import chain
from os import getenv
from random import shuffle
from typing import TYPE_CHECKING, Dict, List

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


class SortingType(Enum):
    sequential = 1
    shuffled = 2
    semi_shuffled = 3
    staggered = 4


def _get_episodes(
    ssn: 'Session',
    series_names: List[str]
) -> Dict[int, List[int]]:
    """Get all episode ratingkeys of the series.

    Args:
        ssn (Session): The plex requests session to fetch with.
        series_names (List[str]): The names of the series to get the episodes
        from.

    Returns:
        Dict[int, List[int]]: Map of the series rating key to a list of the
        episode rating keys.
    """
    # {series_ratingkey: [episode_keys, ...]}
    series_episodes: Dict[int, List[int]] = {}

    for series in series_names:
        search_results: List[dict] = ssn.get(
            f'{base_url}/search',
            params={'query': series}
        ).json()['MediaContainer'].get('Metadata', [])

        for search_result in search_results:
            if (
                search_result['title'] == series
                and search_result['type'] == 'show'
            ):
                break
        else:
            continue

        # Series found
        series_output = ssn.get(
            f'{base_url}/library/metadata/{search_result["ratingKey"]}/allLeaves'
        ).json()['MediaContainer'].get('Metadata', [])

        series_episodes[search_result['ratingKey']] = [
            e['ratingKey'] for e in series_output
        ]

    return series_episodes


def _create_sequential(series_episodes: Dict[int, List[int]]) -> List[int]:
    return list(chain(*series_episodes.values()))


def _create_shuffled(series_episodes: Dict[int, List[int]]) -> List[int]:
    episodes = _create_sequential(series_episodes)
    shuffle(episodes)
    return episodes


def _create_semi_shuffled(series_episodes: Dict[int, List[int]]) -> List[int]:
    episodes = []
    for series in series_episodes.values():
        shuffle(series)
        episodes += series
    return episodes


def _create_staggered(series_episodes: Dict[int, List[int]]) -> List[int]:
    episodes = []
    series_list = list(series_episodes.values())
    range_list = max([len(l) for l in series_list])
    for index in range(range_list):
        for series in series_list:
            try:
                episodes.append(series[index])
            except IndexError:
                pass
    return episodes


order_executors = {
    SortingType.sequential.value: _create_sequential,
    SortingType.shuffled.value: _create_shuffled,
    SortingType.semi_shuffled.value: _create_semi_shuffled,
    SortingType.staggered.value: _create_staggered
}


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


def advanced_playlist(
    ssn: 'Session',
    series_names: List[str], order: SortingType,
    playlist_name: str, users: List[str] = ['@me']
) -> List[int]:
    """Make a playlist with the desired sersies in it and most importantly, in
    the order that you want: sequential, shuffled, semi-shuffled or staggered.

    Args:
        ssn (Session): The plex requests session to fetch with.
        series_names (List[str]): The names of the series to put in the playlist.
        order (SortingType): The ordering of the playlist.
        playlist_name (str): The name of the playlist.
        users (List[str], optional): The lsit of users to apply the selection for.
            Defaults to ['@me'].

    Returns:
        List[int]: List of media rating keys taht were processed.
    """
    series_episodes = _get_episodes(ssn, series_names)

    episodes = order_executors[order.value](series_episodes)

    user_tokens = _gather_user_tokens(ssn, users)

    machine_id = ssn.get(
        f'{base_url}/'
    ).json()['MediaContainer']['machineIdentifier']

    for token in user_tokens:
        # If playlist with this name already exists, remove it first
        playlists = ssn.get(
            f'{base_url}/playlists',
            params={'X-Plex-Token': token}
        ).json()['MediaContainer'].get('Metadata', [])

        for playlist in playlists:
            if playlist['title'] == playlist_name:
                ssn.delete(
                    f'{base_url}/playlists/{playlist["ratingKey"]}',
                    params={'X-Plex-Token': token}
                )

        # Create playlist
        ssn.post(
            f'{base_url}/playlists',
            params={
                'type': 'video',
                'title': playlist_name,
                'smart': '0',
                'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join((str(e) for e in episodes))}',
                'X-Plex-Token': token})

    return episodes


if __name__ == '__main__':
    from argparse import ArgumentParser, RawTextHelpFormatter

    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    epilog = """
The orders explained:
    sequential
        The complete series are added after each other
    shuffled
        All episodes of all series are shuffled through each other
    semi-shuffled
        The series are sequential but "inside" the series, the episodes are shuffled
    staggered
        The first episode of each series is added, then the second of each series, etc.
"""

    parser = ArgumentParser(
        formatter_class=RawTextHelpFormatter,
        description="Make a playlist with the desired sersies in it and most importantly, in the order that you want: sequential, shuffled, semi-shuffled or staggered.",
        epilog=epilog
    )

    parser.add_argument('-s', '--SeriesName', type=str, action='append', required=True, help="Select a series to put in the playlist based on it's name; allowed to give argument multiple times")
    parser.add_argument('-o', '--Order', required=True, choices=SortingType._member_names_, help="The way the series should be ordered in the playlist")
    parser.add_argument('-n', '--PlaylistName', required=True, type=str, help="The name of the playlist that will be created")
    parser.add_argument('-u', '--User', type=str, action='append', default=['@me'], help="Select the user(s) to apply this script to; Give username, '@me' for yourself or '@all' for everyone; allowed to give argument multiple times")
    # autopep8: off

    args = parser.parse_args()

    advanced_playlist(
        ssn,
        args.SeriesName, SortingType[args.Order],
        args.PlaylistName, args.User
    )
