#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Put all requested movies from overseerr in a collection in plex.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 overseerr_to_collection.py -h
        or
        python overseerr_to_collection.py -h
    3. Run this script at an interval to keep the collection updated.
        Decide for yourself what the interval is (e.g. every 12h or every 2 days).

Examples:
    --LibraryName "Movies" --CollectionName "Requested Movies"

        Create a collection called "Requested Movies" in the library called
        "Movies" with all requested movies in it (that are in that library).
"""

from os import getenv
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from requests import Session

# ===== FILL THESE VARIABLES =====
plex_base_url = ''
plex_api_token = ''
overseerr_base_url = ''
overseerr_api_token = ''
# ================================

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
overseerr_base_url = getenv('overseerr_base_url', overseerr_base_url)
overseerr_api_token = getenv('overseerr_api_token', overseerr_api_token)
p_base_url = plex_base_url.rstrip('/')
o_base_url = overseerr_base_url.rstrip('/') + "/api/v1"


def overseerr_to_collection(
    plex_ssn: 'Session',
    overseerr_ssn: 'Session',
    library_name: str,
    collection_name: str = "Overseerr Requests"
) -> List[int]:
    """Put all requested movies from overseerr in a collection in plex.

    Args:
        plex_ssn (Session): The plex requests session to fetch with.

        overseerr_ssn (Session): The overseerr requests session to fetch with.

        library_name (str): Movie library to put the collection in.

        collection_name (str, optional): Name of the collection.
            Defaults to "Overseerr Requests".

    Raises:
        ValueError: Library not found.

    Returns:
        List[int]: List of media rating keys that are in the collection.
    """
    result_json = []

    # Find plex library
    sections = plex_ssn.get(
        f'{p_base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])

    for lib in sections:
        if lib['title'] == library_name:
            break
    else:
        raise ValueError("Library not found")

    # Note down plex rating key of every requested and downloaded
    # movie in overseerr

    offset = 0
    while 1:
        requests: List[dict] = overseerr_ssn.get(
            f'{o_base_url}/request',
            params={
                'filter': 'available',
                'take': 50,
                'skip': offset
            }
        ).json().get('results', [])

        if not requests:
            break

        for request in requests:
            if request['type'] != 'movie':
                continue

            if request['media']['ratingKey4k']:
                result_json.append(request['media']['ratingKey4k'])

            elif request['media']['ratingKey']:
                result_json.append(request['media']['ratingKey'])

        offset += 50

    # Delete collection if it exists
    collections = plex_ssn.get(
        f'{p_base_url}/library/sections/{lib["key"]}/collections'
    ).json()['MediaContainer'].get('Metadata', [])

    for collection in collections:
        if collection == collection_name:
            plex_ssn.delete(
                f'{p_base_url}/library/collections/{collection["ratingKey"]}'
            ).json()
            break

    # Create collection
    machine_id = plex_ssn.get(
        f'{p_base_url}/'
    ).json()['MediaContainer']['machineIdentifier']

    plex_ssn.post(
        f'{p_base_url}/library/collections',
        params={
            'title': collection_name,
            'smart': '0',
            'sectionId': lib["key"],
            'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(result_json)}'
        }
    )

    return [int(e) for e in result_json]


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup vars
    plex_ssn = Session()
    plex_ssn.headers.update({'Accept': 'application/json'})
    plex_ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore
    overseerr_ssn = Session()
    overseerr_ssn.headers.update({'X-Api-Key': overseerr_api_token})

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Put all requested movies from overseerr in a collection in plex.")
    parser.add_argument('-l', '--LibraryName', type=str, required=True, help="Name of target movie library")
    parser.add_argument('-c', '--CollectionName', type=str, default="Overseerr Requests", help="Name of collection that movies will be put in")
    # autopep8: on

    args = parser.parse_args()

    try:
        overseerr_to_collection(
            plex_ssn, overseerr_ssn,
            args.LibraryName, args.CollectionName
        )

    except ValueError as e:
        parser.error(e.args[0])
