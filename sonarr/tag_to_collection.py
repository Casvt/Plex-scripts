#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Put all movies (Radarr) or series (Sonarr) with a certain tag
    in a collection in Plex.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 tag_to_collection.py -h
        or
        python tag_to_collection.py -h

Examples:
    --Source "radarr" --TagName "serious" --LibraryName "Films" --CollectionName "Serious Movies"

        In Radarr, grab all movies tagged with the tag "serious" and put them
        in a collection called "Serious Movies" in the "Films" library.

    -s "sonarr" -t "short" -l "Tv-series" --CollectionName "Short Series"

        In Sonarr, grab all shows tagged with the tag "short" and put them
        in a collection called "Short Series" in the "Tv-series" library.
"""

from enum import Enum
from os import getenv
from typing import TYPE_CHECKING, Dict, List, Union

if TYPE_CHECKING:
    from requests import Session

# ===== FILL THESE VARIABLES ===================
plex_base_url = ''
plex_api_token = ''
# ===== FILL THESE VARIABLES TO USE SONARR =====
sonarr_base_url = ''
sonarr_api_token = ''
# ===== FILL THESE VARIABLES TO USE RADARR =====
radarr_base_url = ''
radarr_api_token = ''
# ==============================================

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
sonarr_base_url = getenv('sonarr_base_url', sonarr_base_url)
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
radarr_base_url = getenv('radarr_base_url', radarr_base_url)
radarr_api_token = getenv('radarr_api_token', radarr_api_token)
p_base_url = plex_base_url.rstrip('/')
s_base_url = sonarr_base_url.rstrip('/') + '/api/v3'
r_base_url = radarr_base_url.rstrip('/') + '/api/v3'


class SoftwareType(Enum):
    radarr = 1
    sonarr = 2


def _sonarr(
    sonarr_ssn: 'Session',
    tag_name: str
) -> List[str]:

    series_list: List[dict] = sonarr_ssn.get(
        f'{s_base_url}/series'
    ).json()

    # Find id of tag
    tags = sonarr_ssn.get(
        f'{s_base_url}/tag'
    ).json()
    print(tags)
    for tag in tags:
        if tag['label'] == tag_name:
            break
    else:
        raise ValueError("Tag not found")

    # Add series of tag to result
    result_json: List[str] = [
        s['path']
        for s in series_list
        if tag['id'] in s['tags']
    ]
    return result_json


def _radarr(
    radarr_ssn: 'Session',
    tag_name: str
) -> List[str]:

    movie_list = radarr_ssn.get(
        f'{r_base_url}/movie'
    ).json()

    # Find id of tag
    tags = radarr_ssn.get(
        f'{r_base_url}/tag'
    ).json()
    for tag in tags:
        if tag['label'] == tag_name:
            break
    else:
        raise ValueError("Tag not found")

    # Add movies of tag to result
    result_json: List[str] = [
        m['movieFile']['path']
        for m in movie_list
        if 'movieFile' in m
        and tag['id'] in m['tags']
    ]
    return result_json


def tag_to_collection(
    plex_ssn: 'Session',
    radarr_ssn: Union['Session', None],
    sonarr_ssn: Union['Session', None],
    source: SoftwareType,
    tag_name: str,
    library_name: str,
    collection_name: str
) -> List[int]:
    """Put all movies (Radarr) or series (Sonarr) with a certain tag
    in a collection in Plex.

    Args:
        plex_ssn (Session): The plex requests session to fetch with.

        radarr_ssn (Union[Session, None]): The radarr requests
        session to fetch with, if radarr is the source to work on.

        sonarr_ssn (Union[Session, None]): The sonarr requests
        session to fetch with, if sonarr is the source to work on.

        source (SoftwareType): The type to work on.

        tag_name (str): The name of the tag to make the collection out of.

        library_name (str): The name of the library to put the collection in.

        collection_name (str): The name of the collection.

    Raises:
        ValueError: Library not found.
        ValueError: Service requested that is not set up.
        ValueError: Tag not found.

    Returns:
        List[int]: List of plex rating keys that were put in the collection.
    """
    # Find plex library
    sections = plex_ssn.get(
        f'{p_base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])

    for lib in sections:
        if lib['title'] == library_name:
            break
    else:
        raise ValueError("Library not found")

    lib_content: List[dict] = plex_ssn.get(
        f'{p_base_url}/library/sections/{lib["key"]}/all',
        params={"type": "1" if lib["type"] == "movie" else "4"}
    ).json()['MediaContainer'].get('Metadata', [])

    if lib["type"] == "movie":
        key_type = "ratingKey"
    else:
        key_type = "grandparentRatingKey"

    file_to_key: Dict[str, str] = {
        part['file']: c[key_type]
        for c in lib_content
        for media in c.get('Media', [])
        for part in media.get('Part', [])
    }

    # Get plex rating keys of collection entries
    if (
        source == SoftwareType.sonarr
        and sonarr_ssn is not None
    ):
        files = _sonarr(sonarr_ssn, tag_name)

    elif (
        source == SoftwareType.radarr
        and radarr_ssn is not None
    ):
        files = _radarr(radarr_ssn, tag_name)

    else:
        raise ValueError("Service requested that is not set up")

    if source == SoftwareType.radarr:
        result_json = [
            file_to_key[f]
            for f in files
        ]

    else: # sonarr
        result_json: List[str] = []
        for f in files:
            for key, value in file_to_key.items():
                if key.startswith(f):
                    result_json.append(value)
                    break

    # If collection with this name already exists, remove it first
    collections = plex_ssn.get(
        f'{p_base_url}/library/sections/{lib["key"]}/collections'
    ).json()['MediaContainer'].get('Metadata', [])
    for collection in collections:
        if collection['title'] == collection_name:
            plex_ssn.delete(
                f'{p_base_url}/library/collections/{collection["ratingKey"]}'
            )

    # Create collection
    machine_id = plex_ssn.get(
        f'{p_base_url}/'
    ).json()['MediaContainer']['machineIdentifier']

    plex_ssn.post(
        f'{p_base_url}/library/collections',
        params={
            'type': "1" if lib["type"] == "movie" else "2",
            'title': collection_name,
            'smart': '0',
            'sectionId': lib["key"],
            'uri': f'server://{machine_id}/com.plexapp.library/library/metadata/{",".join(result_json)}'
        }
    )
    return [int(rk) for rk in result_json]


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup vars
    plex_ssn = Session()
    plex_ssn.headers.update({'Accept': 'application/json'})
    plex_ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Put all movies (Radarr) or series (Sonarr) with a certain tag in a collection in Plex.")
    parser.add_argument('-s', '--Source', type=str, choices=SoftwareType._member_names_, required=True, help="Select the source which entries should be processed")
    parser.add_argument('-t', '--TagName', type=str, required=True, help="Name of tag to search create the collection for")
    parser.add_argument('-l', '--LibraryName', type=str, required=True, help="Name of the target library to put the collection in")
    parser.add_argument('-c', '--CollectionName', type=str, required=True, help="Name of the collection")
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
                {'apikey': sonarr_api_token}
            )

        tag_to_collection(
            plex_ssn, radarr_ssn, sonarr_ssn,
            source,
            args.TagName,
            args.LibraryName, args.CollectionName
        )

    except ValueError as e:
        parser.error(e.args[0])
