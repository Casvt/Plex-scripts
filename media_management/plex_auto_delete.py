#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Set the value of the shows setting "auto delete after watching" for
    all the selected shows.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 plex_auto_delete.py -h
        or
        python plex_auto_delete.py -h
"""

from enum import Enum
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


class ValueMapping(Enum):
    never = '0'
    after_day = '1'
    after_week = '7'


def plex_auto_delete(
    ssn: 'Session', value: ValueMapping,
    library_name: str, series_names: List[str] = []
) -> List[int]:
    """Set the value of the shows setting "auto delete after watching" for
    all the selected shows.

    Args:
        ssn (Session): The plex requests session to fetch with.
        value (ValueMapping): The value of the setting.
        library_name (str): The name of the library to target.
        series_names (List[str], optional): The names of the series to
        specifically target in the library.
            Defaults to [].

    Returns:
        List[int]: List of media rating keys that were processed.
    """
    result_json = []

    sections = ssn.get(
        f'{base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])

    for lib in sections:
        if lib['type'] != 'show':
            continue
        if lib['title'] != library_name:
            continue

        print(lib['title'])

        lib_output = ssn.get(
            f'{base_url}/library/sections/{lib["key"]}/all'
        ).json()['MediaContainer'].get('Metadata', [])

        for show in lib_output:
            if series_names and not show['title'] in series_names:
                continue

            print(f'    {show["title"]}')
            ssn.put(
                f'{base_url}/library/metadata/{show["ratingKey"]}/prefs',
                params={'autoDeletionItemPolicyWatchedLibrary': value.value}
            )
            result_json.append(show['ratingKey'])

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
    parser = ArgumentParser(description="Set the value of the shows setting 'auto delete after watching' for all the selected shows.")
    parser.add_argument('-v', '--Value', choices=ValueMapping._member_names_, required=True, help="The value that the setting should be set to")
    parser.add_argument('-l', '--LibraryName', type=str, required=True, help="Name of target show library")
    parser.add_argument('-s', '--SeriesName', type=str, action='append', default=[], help="Target a specific series inside a show library based on it's name; allowed to give argument multiple times")
    # autopep8: on

    args = parser.parse_args()

    plex_auto_delete(
        ssn, args.Value,
        args.LibraryName, args.SeriesName
    )
