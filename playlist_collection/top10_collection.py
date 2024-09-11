#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Make a collection with the top 10 most popular movies.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 top10_collection.py -h
        or
        python top10_collection.py -h
    3. Run this script at an interval to keep the collection updated.
        Decide for yourself what the interval is (e.g. every 24h or once every week).

Examples:
    --LibraryName "Films"

        Create a collection of the top 10 most watched movies in the "Films"
        library and call the collection "Top 10 Movies".

    -l "Movies" -t "Most Watched Movies"

        Create a collection of the top 10 most watched movies in the "Movies"
        library and call the collection "Most Watched Movies".
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


def _get_library_id(
    ssn: 'Session',
    library_name: str
) -> int:
    """Get library ID based on it's name.

    Args:
        ssn (Session): The plex requests session to fetch with.
        library_name (str): The name of the library to get the ID of.

    Raises:
        ValueError: Library not found.

    Returns:
        int: The ID of the library.
    """
    sections: List[dict] = ssn.get(
        f'{base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])

    for lib in sections:
        if lib['title'] == library_name:
            return int(lib['key'])

    raise ValueError("Library not found")


def _get_top10(
    ssn: 'Session',
    library_id: int
) -> List[int]:
    """Get the top 10 most watched movies of a library.

    Args:
        ssn (Session): The plex requests session to fetch with.
        library_id (int): The ID of the library to get the list for.

    Returns:
        List[int]: The media rating keys of the top 10 most watched movies, in
        order of watch count.
    """
    movies = ssn.get(
        f'{base_url}/library/sections/{library_id}/all',
        params={
            'sort': 'viewCount:desc',
            'X-Plex-Container-Start': '0',
            'X-Plex-Container-Size': '10'
        }
    ).json()['MediaContainer'].get('Metadata', [])

    return [int(m['ratingKey']) for m in movies]


def top10_collection(
    ssn: 'Session',
    library_name: str,
    collection_title: str = "Top 10 Movies"
) -> List[int]:
    """Make a collection with the top 10 most popular movies.

    Args:
        ssn (Session): The plex requests session to fetch with.
        library_name (str): The name of the target library.
        collection_title (str, optional): The title of the collection.
            Defaults to "Top 10 Movies".

    Returns:
        List[int]: List of media rating keys that are in the collection.
    """
    lib_id = _get_library_id(ssn, library_name)
    top10 = _get_top10(ssn, lib_id)

    # If collection with this name already exists, remove it first
    lib_collections: List[dict] = ssn.get(
        f'{base_url}/library/sections/{lib_id}/collections'
    ).json()['MediaContainer'].get('Metadata', [])
    for collection in lib_collections:
        if collection['title'] == collection_title:
            ssn.delete(
                f'{base_url}/library/collections/{collection["ratingKey"]}'
            )
            break

    # Create collection
    machine_id = ssn.get(
        f'{base_url}/'
    ).json()['MediaContainer']['machineIdentifier']
    ssn.post(
        f'{base_url}/library/collections',
        params={
            'type': '1',
            'title': collection_title,
            'smart': '0',
            'sectionId': lib_id,
            'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join((str(e) for e in top10))}'
        }
    )

    return top10


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Make a collection with the top 10 most popular movies of a library.")
    parser.add_argument('-l', '--LibraryName', type=str, required=True, help="The name of the target library")
    parser.add_argument('-t', '--CollectionTitle', type=str, default="Top 10 Movies", help="The title of the collection")
    # autopep8: on

    args = parser.parse_args()

    try:
        top10_collection(ssn, args.LibraryName, args.CollectionTitle)

    except ValueError as e:
        parser.error(e.args[0])
