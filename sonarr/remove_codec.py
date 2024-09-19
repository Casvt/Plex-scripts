#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Delete media files in Sonarr/Radarr that have the codec given
    and initiate a new search for them.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 remove_codec.py -h
        or
        python remove_codec.py -h

Examples:
    --Source radarr --Codec x264

        Find all movies on Radarr that have the x264 codec.
        Then delete them and initiate a search.

    -s sonarr -c av1

        Find all episodes on Sonarr that have the av1 codec.
        Then delete them and initiate a search.
"""

from enum import Enum
from os import getenv
from typing import TYPE_CHECKING, List, Union

if TYPE_CHECKING:
    from requests import Session

# ===== FILL THESE VARIABLES TO USE SONARR =====
sonarr_base_url = ''
sonarr_api_token = ''
# ===== FILL THESE VARIABLES TO USE RADARR =====
radarr_base_url = ''
radarr_api_token = ''
# ==============================================

# Environmental Variables
sonarr_base_url = getenv('sonarr_base_url', sonarr_base_url)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
radarr_base_url = getenv('radarr_base_url', radarr_base_url)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)
s_base_url = sonarr_base_url.rstrip('/') + '/api/v3'
r_base_url = radarr_base_url.rstrip('/') + '/api/v3'


class SoftwareType(Enum):
    radarr = 1
    sonarr = 2


def _sonarr(
    sonarr_ssn: 'Session',
    codec: str
) -> List[int]:

    result_json: List[int] = []
    series_list: List[dict] = sonarr_ssn.get(
        f'{sonarr_base_url}/series'
    ).json()

    for series in series_list:
        episode_list: List[dict] = sonarr_ssn.get(
            f'{sonarr_base_url}/episode',
            params={'seriesId': series['id']}
        ).json()

        for episode in episode_list:
            episode_output: dict = sonarr_ssn.get(
                f'{sonarr_base_url}/episodeFile/{episode["episodeFileId"]}'
            ).json()

            if episode_output['mediaInfo']['videoCodec'] != codec:
                continue

            # Episode matches codec; replace it
            print(episode_output['path'])
            sonarr_ssn.delete(
                f'{sonarr_base_url}/episodeFile/{episode_output["id"]}',
                params={'episodeEntity': 'episodes'}
            )
            sonarr_ssn.post(
                f'{sonarr_base_url}/command',
                json={
                    'name': 'EpisodeSearch',
                    'episodeIds': [episode['id']]
                }
            )
            result_json.append(episode['id'])

    return result_json


def _radarr(
    radarr_ssn: 'Session',
    codec: str
) -> List[int]:

    result_json: List[int] = []
    movie_list: List[dict] = radarr_ssn.get(
        f'{radarr_base_url}/movie'
    ).json()

    for movie in movie_list:
        if 'movieFile' not in movie:
            continue
        if movie['movieFile']['mediaInfo']['videoCodec'] != codec:
            continue

        # Movie matches codec; replace it
        print(movie['movieFile']['path'])
        radarr_ssn.delete(
            f'{radarr_base_url}/movieFile/{movie["movieFile"]["id"]}'
        )
        radarr_ssn.post(
            f'{radarr_base_url}/command',
            json={
                'name': 'MoviesSearch',
                'movieIds': [movie['id']]
            }
        )
        result_json.append(movie['id'])

    return result_json


def remove_codec(
    radarr_ssn: Union['Session', None],
    sonarr_ssn: Union['Session', None],
    source: SoftwareType,
    codec: str
) -> List[int]:
    """Delete media files in Sonarr/Radarr that have the codec given
    and initiate a new search for them.

    Args:
        radarr_ssn (Union[Session, None]): The radarr requests
        session to fetch with, if radarr is the source to work on.
        sonarr_ssn (Union[Session, None]): The sonarr requests
        session to fetch with, if sonarr is the source to work on.
        source (SoftwareType): The type to work on.
        codec (str): The codec to search for.

    Returns:
        List[int]: List of media ID's that were processed.
    """
    result_json: List[int] = []

    if (
        source == SoftwareType.sonarr
        and sonarr_ssn is not None
    ):
        result_json = _sonarr(sonarr_ssn, codec)

    elif (
        source == SoftwareType.radarr
        and radarr_ssn is not None
    ):
        result_json = _radarr(radarr_ssn, codec)

    return result_json


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Delete media files in Sonarr/Radarr that have the codec given and initiate a new search for them.")
    parser.add_argument('-s', '--Source', type=str, choices=SoftwareType._member_names_, required=True, help="Select the source which media files should be checked")
    parser.add_argument('-c', '--Codec', type=str, required=True, help="Media files with this codec will be removed and a new search will be initiated")
    # autopep8: on

    args = parser.parse_args()

    try:
        source = SoftwareType[args.Source]
        radarr_ssn, sonarr_ssn = None, None

        if source == SoftwareType.radarr:
            if not (radarr_base_url and radarr_api_token):
                raise ValueError("Radarr not set up")

            radarr_ssn = Session()
            radarr_ssn.params.update( # type: ignore
                {'apikey': radarr_api_token}
            )

        elif source == SoftwareType.sonarr:
            if not (sonarr_base_url and sonarr_api_token):
                raise ValueError("Sonarr not set up")

            sonarr_ssn = Session()
            sonarr_ssn.params.update( # type: ignore
                {'apikey': radarr_api_token}
            )

        remove_codec(
            radarr_ssn, sonarr_ssn,
            source, args.Codec
        )

    except ValueError as e:
        parser.error(e.args[0])
