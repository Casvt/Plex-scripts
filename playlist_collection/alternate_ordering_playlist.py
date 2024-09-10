#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Create a playlist with a series in it but with an alternate order
    coming from the tvdb.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 alternate_ordering_playlist.py -h
        or
        python alternate_ordering_playlist.py -h

Examples:
    --SeriesName "Pokémon" --GetOrders

        List the available orders for the series "Pokémon"

    -s "Initial D" -o "Aired Order" -a

        Make a playlist for the series "Initial D", and order it according to
        the "Aired Order" ordering. Add any episodes that weren't found on tvdb
        at the end of the playlist.
"""

from os import getenv
from re import DOTALL, compile
from typing import TYPE_CHECKING, Any, Dict, List, Union

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
tvdb_base_url = 'https://thetvdb.com'
order_regex = compile(
    r'href="#seasons-(\w+?)" class="change_seasontype"[^>]+>(.*?)<')
episode_regex = compile(
    r'episode-label">[^>]+>\s+<a href="[^\d]+(\d+)">',
    DOTALL)


def _find_series(
    ssn: 'Session',
    series_name: str
) -> Dict[str, Any]:
    search_results: List[dict] = ssn.get(
        f'{base_url}/search',
        params={
            'query': series_name,
            'includeGuids': '1'
        }
    ).json()['MediaContainer'].get('Metadata', [])

    for search_result in search_results:
        if (
            search_result['title'] == series_name
            and search_result['type'] == 'show'
        ):
            break
    else:
        raise ValueError("Show not found")

    return search_result


def _get_tvdb_id(data: Dict[str, List[Dict[str, str]]]) -> Union[str, None]:
    return next(
        iter((
            g['id'].split('/')[-1]
            for g in data.get('Guid', [])
            if g['id'].startswith('tvdb://')
        )),
        None
    )


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


def alternate_ordering_playlist(
    ssn: 'Session',
    series_name: str,
    get_orders: bool = False,
    order: Union[str, None] = None,
    add_unknown: bool = False,
    no_watched: bool = False,
    users: List[str] = ['@me']
) -> Union[List[int], List[str]]:
    result_json: List[int] = []

    # Check for illegal arg parsing
    if not get_orders and order is None:
        raise ValueError("Either request the orders or make a playlist")

    series = _find_series(ssn, series_name)

    show_guid = _get_tvdb_id(series)

    if not show_guid:
        raise ValueError("Show is not matched to the TVDB")

    tvdb_info = ssn.get(
        f'{tvdb_base_url}/dereferrer/series/{show_guid}'
    )
    orders: Dict[str, str] = dict((
        reversed(o)
        for o in order_regex.findall(tvdb_info.text)
    )) # type: ignore

    if get_orders:
        return list(orders.keys())

    if order not in orders:
        raise ValueError("Order not found")

    order_link = f"{tvdb_base_url}{tvdb_info.url.split(tvdb_base_url)[1]}/allseasons/{orders[order]}"
    order_content = ssn.get(order_link).text
    tvdb_ids: List[str] = episode_regex.findall(order_content)

    # tvdb id -> plex rating key of episode
    id_map: Dict[str, int] = {}
    no_id: List[int] = []

    series_content = ssn.get(
        f'{base_url}/library/metadata/{series["ratingKey"]}/allLeaves',
        params={'includeGuids': '1'}
    ).json()['MediaContainer'].get('Metadata', [])

    for episode in series_content:
        if no_watched and 'viewCount' in episode:
            continue
        guid = _get_tvdb_id(episode)
        if guid:
            id_map[guid] = int(episode['ratingKey'])
        elif add_unknown:
            no_id.append(int(episode['ratingKey']))

    for tvdb_id in tvdb_ids:
        if tvdb_id in id_map:
            result_json.append(id_map[tvdb_id])

    if add_unknown:
        result_json += no_id

    if not result_json:
        return result_json

    user_tokens = _gather_user_tokens(ssn, users)

    machine_id = ssn.get(
        f'{base_url}/'
    ).json()['MediaContainer']['machineIdentifier']

    playlist_name = f"{series['title']} - {order}"

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
                'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join((str(e) for e in result_json))}',
                'X-Plex-Token': token})

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
    parser = ArgumentParser(description="Create a playlist with a series in it but with an alternate order coming from the tvdb.")
    parser.add_argument('-s', '--SeriesName', type=str, required=True, help="The series to create the playlist for, based on it's name")

    parser.add_argument('-g', '--GetOrders', action='store_true', help="List the tvdb orders available for the series and exit")

    parser.add_argument('-o', '--Order', type=str, help="Name of tvdb order that should be applied")
    parser.add_argument('-a', '--AddUnknown', action='store_true', help="Add all episodes of the show that weren't found in the tvdb to the end of the playlist")
    parser.add_argument('-w', '--NoWatched', action='store_true', help="Don't add episodes that are marked as watched")

    parser.add_argument('-u', '--User', type=str, action='append', default=['@me'], help="Select the user(s) to apply this script to; Give username, '@me' for yourself or '@all' for everyone; allowed to give argument multiple times")
    # autopep8: on

    args = parser.parse_args()

    try:
        result = alternate_ordering_playlist(
            ssn=ssn,
            series_name=args.SeriesName,
            get_orders=args.GetOrders,
            order=args.Order,
            add_unknown=args.AddUnknown,
            no_watched=args.NoWatched,
            users=args.User
        )

    except ValueError as e:
        parser.error(e.args[0])

    if not result:
        print("No orders found or no playlist to make")

    elif isinstance(result[0], str):
        for order in result:
            print(order)
