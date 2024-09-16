#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Give the ID of a IMDb/TVDb/TMDb list and make a collection in plex
    of the movies/episodes in the list.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 list_to_collection.py -h
        or
        python list_to_collection.py -h

Examples:
    --Source "IMDb" --Id "ls091520106" --LibraryName "Films"

        Create a collection in the "Films" library with the media entries of the
        IMDb list with ID "ls091520106".

    --Source "TVDb" --Id "marvel-cinematic-universe" --LibraryName "Tv-series"

        Create a collection in the "Tv-series" library with the media entries of
        the TVDb official list called "marvel-cinematic-universe".

    -s "TVDb" -i "14621" -l "Tv-series"

        Create a collection in the "Tv-series" library with the media entries of
        the TVDb list with ID "14621".

    -s "TMDb" -i "502" -l "Films"

        Create a collection in the "Films" library with the media entries of the
        TMDb list with ID "502".
"""

from enum import Enum
from json import loads
from os import getenv
from re import DOTALL, compile
from typing import TYPE_CHECKING, Dict, List, Tuple

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


# autopep8: off
USER_AGENT = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36"
imdb_title_regex = compile(r'(?<=<title>).*?(?=</title>)')
imdb_content_regex = compile(r'(?<=<script type="application/ld\+json">).*?(?=</script>)')
tvdb_title_regex = compile(r'id="series_title">([^<]+?)</h1>')
tvdb_content_regex = compile(r'<a.*?<img class="img-responsive img-rounded"[^>]+?/(\d+)(?:-\d+)?(?:/|.jpg).*?</a>', DOTALL)
tmdb_title_regex = compile(r'<h2[^>]+>(.*?)</h2>')
tmdb_content_regex = compile(r'<div[^>]+md:table-cell[^<]+<span[^<]+<a.*?href="[^\"]+/(\d+)')
# autopep8: on


class ListSource(Enum):
    IMDb = 1
    TVDb = 2
    TMDb = 3


def _get_imdb_ids(ssn: 'Session', list_id: str) -> Tuple[str, List[str]]:
    r = ssn.get(
        f'https://www.imdb.com/list/{list_id}/',
        headers={'User-Agent': USER_AGENT}
    )
    if r.status_code != 200:
        raise ValueError("List not found")
    list_content = r.text

    list_title = imdb_title_regex.search(list_content)
    if not list_title:
        raise ValueError("Failed to extract list")
    list_title = list_title.group()
    print(list_title)

    list_json = imdb_content_regex.search(list_content)
    if not list_json:
        raise ValueError("Failed to extract list")

    list_ids = [
        'imdb://' + entry['item']['url'].rstrip('/').split('/')[-1]
        for entry in loads(list_json.group())['itemListElement']
    ]

    if not list_ids:
        raise ValueError("List is empty")

    return list_title, list_ids


def _get_tvdb_ids(ssn: 'Session', list_id: str) -> Tuple[str, List[str]]:
    r = ssn.get(
        f'https://thetvdb.com/lists/{list_id}',
        headers={'User-Agent': USER_AGENT}
    )
    if r.status_code != 200:
        raise ValueError("List not found")
    list_content = r.text

    list_title = tvdb_title_regex.search(list_content)
    if not list_title:
        raise ValueError("Failed to extract list")
    list_title = list_title.group(1).strip()
    print(list_title)

    list_ids = [
        'tvdb://' + entry
        for entry in tvdb_content_regex.findall(list_content)
    ]

    if not list_ids:
        raise ValueError("List is empty")

    return list_title, list_ids


def _get_tmdb_ids(ssn: 'Session', list_id: str) -> Tuple[str, List[str]]:
    r = ssn.get(
        f'https://www.themoviedb.org/list/{list_id}',
        headers={'User-Agent': USER_AGENT}
    )
    if r.status_code != 200:
        raise ValueError("List not found")
    list_content = r.text

    list_title = tmdb_title_regex.search(list_content)
    if not list_title:
        raise ValueError("Failed to extract list")
    list_title = list_title.group(1).strip()
    print(list_title)

    list_ids: List[str] = tmdb_content_regex.findall(list_content)

    if not list_ids:
        raise ValueError("List is empty")

    page = 2
    while True:
        page_ids = tmdb_content_regex.findall(
            ssn.get(
                f'https://www.themoviedb.org/list/{list_id}',
                params={'page': page},
                headers={'User-Agent': USER_AGENT}
            ).text
        )
        if not page_ids:
            break
        list_ids += page_ids
        page += 1

    list_ids = ['tmdb://' + e for e in list_ids]

    return list_title, list_ids


SOURCE_TO_IDS = {
    ListSource.IMDb.value: _get_imdb_ids,
    ListSource.TVDb.value: _get_tvdb_ids,
    ListSource.TMDb.value: _get_tmdb_ids,
}

LIB_TO_TYPES = {
    'movie': '1',
    'show': '2',
}


def list_to_collection(
    ssn: 'Session',
    source: ListSource,
    list_id: str,
    library_name: str
) -> List[int]:
    """Give the ID of a IMDb/TVDb/TMDb list and make a collection in plex
    of the movies/episodes in the list.

    Args:
        ssn (Session): The plex requests session to fetch with.
        source (ListSource): The website that the list is from.
        list_id (str): The ID of the list.
        library_name (str): The name of the library to put the collection in.

    Raises:
        ValueError: Library not found.
        ValueError: No entries from the list found in the library.
        ValueError: List not found.
        ValueError: List is empty.
        ValueError: Failed to extract list.

    Returns:
        List[int]: List of media rating keys that are in the collection.
    """
    list_title, list_ids = SOURCE_TO_IDS[source.value](ssn, list_id)

    # Get library information
    sections = ssn.get(
        f'{base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])

    for lib in sections:
        if lib['title'] == library_name:
            break
    else:
        raise ValueError("Library not found")

    lib_id, lib_type = lib['key'], LIB_TO_TYPES[lib['type']]

    # Find media in library
    lib_output: List[dict] = ssn.get(
        f'{base_url}/library/sections/{lib_id}/all',
        params={
            'type': lib_type,
            'includeGuids': '1'
        }
    ).json()['MediaContainer'].get('Metadata', [])

    guid_to_ratingkey: Dict[str, str] = {
        guid['id']: media['ratingKey']
        for media in lib_output
        for guid in media.get('Guid', [])
    }
    result_json = [
        guid_to_ratingkey[list_id]
        for list_id in list_ids
        if list_id in guid_to_ratingkey
    ]
    if not result_json:
        raise ValueError("No entries from the list found in the library")

    # Delete collection if it already exists
    lib_collections = ssn.get(
        f'{base_url}/library/sections/{lib_id}/collections'
    ).json()['MediaContainer'].get('Metadata', [])

    for collection in lib_collections:
        if collection['title'] == list_title:
            ssn.delete(
                f'{base_url}/library/collections/{collection["ratingKey"]}'
            )
            break

    # Create new collection
    machine_id = ssn.get(
        f'{base_url}/'
    ).json()['MediaContainer']['machineIdentifier']

    ssn.post(
        f'{base_url}/library/collections',
        params={
            'title': list_title,
            'smart': '0',
            'sectionId': lib_id,
            'type': lib_type,
            'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(result_json)}'
        }
    )

    return [int(i) for i in result_json]


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Give the ID of a IMDb/TVDb/TMDb list and make a collection in plex of the movies/episodes in the list.")
    parser.add_argument('-s', '--Source', choices=ListSource._member_names_, required=True, help="The source of the list")
    parser.add_argument('-i', '--Id', type=str, required=True, help="The ID of the list")
    parser.add_argument('-l', '--LibraryName', type=str, required=True, help="Name of library to put collection in")
    # autopep8: on

    args = parser.parse_args()

    try:
        list_to_collection(
            ssn, ListSource[args.Source],
            args.Id, args.LibraryName
        )

    except ValueError as e:
        parser.error(e.args[0])
