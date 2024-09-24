#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Refresh Sonarr- or Plex series for all TBA episodes.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 sonarr_refresh_tba.py -h
        or
        python sonarr_refresh_tba.py -h

Examples:
    --Target plex --Target sonarr

        Trigger a refresh for all TBA/TBD episodes found on plex and sonarr.
"""

from enum import Enum
from os import getenv
from typing import TYPE_CHECKING, List, Tuple, Union

if TYPE_CHECKING:
    from requests import Session

# ===== FILL THESE VARIABLES TO USE PLEX =======
plex_base_url = ''
plex_api_token = ''
# ===== FILL THESE VARIABLES TO USE SONARR =====
sonarr_base_url = ''
sonarr_api_token = ''
# ==============================================

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
sonarr_base_url = getenv('sonarr_base_url', sonarr_base_url)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
p_base_url = plex_base_url.rstrip('/')
s_base_url = sonarr_base_url.rstrip('/') + '/api/v3'


class SoftwareType(Enum):
    plex = 1
    sonarr = 2


def _plex(
    plex_ssn: 'Session'
) -> List[int]:
    result_json: List[int] = []

    sections = plex_ssn.get(
        f'{p_base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])

    for lib in sections:
        if lib['type'] != 'show':
            continue

        # Found show library; check every episode
        lib_content = plex_ssn.get(
            f'{p_base_url}/library/sections/{lib["key"]}/all',
            params={'type': '4'}
        ).json()['MediaContainer'].get('Metadata', [])

        for episode in lib_content:
            if (
                episode['title']
                .lower()
                .strip()
                .rstrip('.')
                not in ('tba', 'tbd')
            ):
                continue

            # Episode found that is TBA; refresh it
            print(
                f'{episode["grandparentTitle"]} - S{episode["parentIndex"]}E{episode["index"]}')

            plex_ssn.put(
                f'{p_base_url}/library/metadata/{episode["ratingKey"]}/refresh'
            )

            result_json.append(int(episode['ratingKey']))

    return []


def _sonarr(
    sonarr_ssn: 'Session'
) -> List[int]:
    result_json: List[int] = []

    series_list = sonarr_ssn.get(
        f'{s_base_url}/series'
    ).json()

    for series in series_list:

        series_output = sonarr_ssn.get(
            f'{s_base_url}/episode',
            params={'seriesId': series['id']}
        ).json()

        for episode in series_output:
            if (
                episode['title']
                .lower()
                .strip()
                .rstrip('.')
                not in ('tba', 'tbd')
            ):
                continue

            # Episode found that is TBA; refresh series
            print(f'{series["title"]}')

            sonarr_ssn.post(
                f'{s_base_url}/command',
                json={
                    'name': 'RefreshSeries',
                    'seriesId': series['id']
                }
            )

            result_json.append(series['id'])
            break

    return result_json


def sonarr_refresh_tba(
    plex_ssn: Union['Session', None],
    sonarr_ssn: Union['Session', None],
    sources: List[SoftwareType]
) -> Tuple[List[int], List[int]]:
    """Refresh Sonarr- or Plex series for all TBA episodes.

    Args:
        plex_ssn (Union[Session, None]): The plex requests session
        to fetch with, if plex is one of the sources to work on.

        sonarr_ssn (Union[Session, None]): The sonarr requests session
        to fetch with, if sonarr is one of the sources to work on.

        sources (List[SoftwareType]): The types to work on.

    Returns:
        Tuple[List[int], List[int]]: First list is plex rating keys that were
        updated. Second lists is sonarr series ID's that were updated.
    """
    result_json: Tuple[List[int], List[int]] = ([], [])

    if (
        SoftwareType.plex in sources
        and plex_ssn is not None
    ):
        result_json[0].extend(_plex(plex_ssn))

    if (
        SoftwareType.sonarr in sources
        and sonarr_ssn is not None
    ):
        result_json[1].extend(_sonarr(sonarr_ssn))

    return result_json


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Refresh Sonarr- or Plex series for all TBA episodes.")
    parser.add_argument('-t', '--Target', action='append', required=True, choices=SoftwareType._member_names_)
    # autopep8: on

    args = parser.parse_args()

    try:
        sources = [
            SoftwareType[t]
            for t in args.Target
        ]
        plex_ssn, sonarr_ssn = None, None

        if SoftwareType.plex in sources:
            if not (plex_base_url and plex_api_token):
                raise ValueError("Plex not set up")

            plex_ssn = Session()
            plex_ssn.headers.update({'Accept': 'application/json'})
            plex_ssn.params.update( # type: ignore
                {'X-Plex-Token': plex_api_token})

        elif SoftwareType.sonarr in sources:
            if not (sonarr_base_url and sonarr_api_token):
                raise ValueError("Sonarr not set up")

            sonarr_ssn = Session()
            sonarr_ssn.params.update( # type: ignore
                {'apikey': sonarr_api_token}
            )

        sonarr_refresh_tba(
            plex_ssn, sonarr_ssn,
            sources
        )

    except ValueError as e:
        parser.error(e.args[0])
