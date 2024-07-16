#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Create a collection containing all the movies of the x first actors (and
    optionally of the movie director) of the last viewed movie.
    The collection will be put in the library from where the source movie
    originated.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 actor_collection.py -h
        or
        python actor_collection.py -h
    3. Run this script at an interval to keep the collection updated.
        Decide for yourself what the interval is (e.g. every 5m or every 3h).

Examples:
    --Actors 3 --MovieDirector

        Process the first three actors of the movie and the movie director.

    --Actors 10 --CollectionName "Last Movie Actors"

        Process the first ten actors of the movie, but not the movie director.
        Call the collection "Last Movie Actors".
"""

from os import getenv
from typing import TYPE_CHECKING, Any, Dict, List, Set

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


def actor_collection(
    ssn: 'Session',
    collection_name: str = "Actor Collection",
    actors: int = 5,
    movie_director: bool = False
) -> List[int]:
    """Create a collection containing all the movies of the x first actors (and
    optionally of the movie director) of the last viewed movie.
    The collection will be put in the library from where the source movie
    originated.

    Args:
        ssn (Session): The plex requests session to fetch with.

        collection_name (str, optional): The name of the collection.
            Defaults to "Actor Collection".

        actors (int, optional): How many of the movie actors should be looked at
        to take the movies from to include them in the collection.
            Defaults to 5.

        movie_director (bool, optional): Also include all the movies of
        the director in the collection.
            Defaults to False.

    Returns:
        List[int]: List of media rating keys that were processed.
    """
    result_json = []

    # Search in history for last viewed movie
    history: List[Dict[str, Any]] = ssn.get(
        f'{base_url}/status/sessions/history/all'
    ).json()['MediaContainer'].get('Metadata', [])

    for media in reversed(history):
        if media['type'] == 'movie':
            break
    else:
        return result_json

    media_info = ssn.get(
        f'{base_url}/library/metadata/{media["ratingKey"]}'
    ).json()['MediaContainer']['Metadata'][0]

    if 'Role' not in media_info:
        return result_json

    # Get the ids of the actors to get the movies of
    actor_ids: List[int] = [
        a['id']
        for a in media_info['Role'][0:actors]
    ]

    # Note the movies down that the actors played in
    movie_ratingkeys: Set[str] = set()
    for actor in actor_ids:
        actor_movies: List[Dict[str, Any]] = ssn.get(
            f'{base_url}/library/sections/{media["librarySectionID"]}/all',
            params={'type': '1', 'actor': actor}
        ).json()['MediaContainer'].get('Metadata', [])

        movie_ratingkeys.update((
            m['ratingKey'] for m in actor_movies
        ))

    if movie_director:
        # Get the movies of the movie director too
        director_movies = ssn.get(
            f'{base_url}/library/sections/{media["librarySectionID"]}/all',
            params={
                'type': '1',
                'director': media_info['Director'][0]['id']
            }
        ).json()['MediaContainer'].get('Metadata', [])

        movie_ratingkeys.update((
            m['ratingKey'] for m in director_movies
        ))

    # If collection with this name already exists, remove it first
    collections = ssn.get(
        f'{base_url}/library/sections/{media["librarySectionID"]}/collections'
    ).json()['MediaContainer'].get('Metadata', [])
    for collection in collections:
        if collection['title'] == collection_name:
            ssn.delete(
                f'{base_url}/library/collections/{collection["ratingKey"]}'
            )

    # Create collection
    machine_id = ssn.get(
        f'{base_url}/'
    ).json()['MediaContainer']['machineIdentifier']

    ssn.post(
        f'{base_url}/library/collections',
        params={
            'type': '1',
            'title': collection_name,
            'smart': '0',
            'sectionId': media['librarySectionID'],
            'uri': f'server://{machine_id}/com.plexapp.library/library/metadata/{",".join(movie_ratingkeys)}'
        }
    )
    result_json += [int(rk) for rk in movie_ratingkeys]

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
    parser = ArgumentParser(description="Create a collection containing all the movies of the x first actors (and optionally of the movie director) of the last viewed movie.")
    parser.add_argument('-c','--CollectionName', type=str, default="Actor Collection", help="Name of target collection")
    parser.add_argument('-a','--Actors', type=int, default=5, help="How many of the movie actors should be looked at to take the movies from to include them in the collection")
    parser.add_argument('-d','--MovieDirector', action="store_true", help="Also include all the movies of the director in the collection")
    # autopep8: on

    args = parser.parse_args()

    actor_collection(
        ssn=ssn,
        collection_name=args.CollectionName,
        actors=args.Actors,
        movie_director=args.MovieDirector
    )
