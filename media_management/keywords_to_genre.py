#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Add a keyword to the genre/label list in plex if the keyword is present in
    the keyword list for the media on the IMDB.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 keywords_to_genre.py -h
        or
        python keywords_to_genre.py -h
"""

from fnmatch import filter as fnmatch_filter
from json import loads
from os import getenv
from re import compile
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
json_finder = compile(
    r'(?<=script id="__NEXT_DATA__" type="application/json">).*?(?=</script>)'
)
USER_AGENT = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36"


def keywords_to_genre(
    ssn: 'Session',
    keywords: List[str],
    library_names: List[str],
    movie_names: List[str] = [],
    series_names: List[str] = [],
    skip_locked: bool = False,
    use_label: bool = False
) -> List[int]:
    """Add a keyword to the genre/label list in plex if the keyword is present in
    the keyword list for the media on the IMDB.

    Args:
        ssn (Session): The plex requests session to fetch with.

        keywords (List[str]): The keywords to search for.

        library_names (List[str]): The names of the libraries to cover.

        movie_names (List[str], optional): The movie names to cover.
            Defaults to [].

        series_names (List[str], optional): The series names to cover.
            Defaults to [].

        skip_locked (bool, optional): Skip media if field is locked.
            Defaults to False.

        use_label (bool, optional): Add to keywords to labels instead of genres.
            Defaults to False.

    Returns:
        List[int]: List of media rating keys that were processed.
    """
    result_json = []
    sections = ssn.get(
        f'{base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])
    field = 'genre' if not use_label else 'label'

    for lib in sections:
        if not (
            lib['type'] in ('movie', 'show')
            and lib['title'] in library_names
        ):
            continue

        lib_output: List[dict] = ssn.get(
            f'{base_url}/library/sections/{lib["key"]}/all',
            params={'includeGuids': '1'}
        ).json()['MediaContainer'].get('Metadata', [])

        for media in lib_output:
            if (
                lib['type'] == 'movie'
                and movie_names
                and not media['title'] in movie_names
                or
                lib['type'] == 'show'
                and series_names
                and not media['title'] in series_names
            ):
                continue

            media_output: dict = ssn.get(
                f'{base_url}/library/metadata/{media["ratingKey"]}'
            ).json()['MediaContainer'].get('Metadata', (None,))[0]

            if not media_output:
                continue

            # Skip media if field is locked and skip_locked is True
            if skip_locked:
                if any(
                    l['name'] == field and l['locked']
                    for l in media_output.get('Field', [])
                ):
                    continue

            # Find IMDB id of media otherwise skip
            for guid in media.get('Guid', []):
                if guid['id'].startswith('imdb://'):
                    media_guid = guid['id'].split('/')[-1]
                    break
            else:
                continue

            # Get all genres/labels that media has been tagged with
            current_values = [
                g['tag']
                for g in media_output.get(field.capitalize(), [])
            ]

            # Get all keywords that media has on IMDB
            imdb_info = ssn.get(
                f'https://www.imdb.com/title/{media_guid}/keywords',
                headers={'User-Agent': USER_AGENT}
            ).text
            re_result = json_finder.search(imdb_info)
            if not re_result:
                continue
            imdb_json = loads(re_result.group(0))
            media_keywords = [
                e['rowTitle']
                for e in imdb_json['props']['pageProps']['contentData'
                ]['section']['items']
                if e['userVotingProps']['itemType'] == 'TitleKeyword'
            ]

            # Find keywords that are desired to be added but aren't already
            new_values = []
            for k in keywords:
                if '*' in k:
                    result = fnmatch_filter(media_keywords, k)
                    new_values += [r for r in result if r not in current_values]
                else:
                    if k in media_keywords and k not in current_values:
                        new_values.append(k)

            # Push new values
            payload = {
                'type': '2' if media['type'] == 'show' else '1',
                'id': media['ratingKey'],
                f'{field}.locked': '1',
                **{
                    f'{field}[{c}].tag.tag': v
                    for c, v in enumerate(current_values + new_values)
                }
            }
            ssn.put(
                f'{base_url}/library/sections/{lib["key"]}/all',
                params=payload
            )

            result_json.append(media['ratingKey'])

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
    parser = ArgumentParser(description="Add a keyword to the genre/label list in plex if the keyword is present in the keyword list for the media on the IMDB.")
    parser.add_argument('-k', '--Keyword', type=str, action='append', required=True, help='Keyword that will be added if found in keyword list; allowed to give multiple times; supports wildcards (*)')
    parser.add_argument('-S', '--SkipLocked', action='store_true', help="Skip media that has it's field locked")
    parser.add_argument('-L', '--UseLabel', action='store_true', help="Put keywords in label fields instead of genre field")

    ts = parser.add_argument_group(title="Target Selectors")
    ts.add_argument('-l', '--LibraryName', type=str, action='append', default=[], required=True, help="Name of target library; allowed to give argument multiple times")
    ts.add_argument('-m', '--MovieName', type=str, action='append', default=[], help="Target a specific movie inside a movie library based on it's name; allowed to give argument multiple times")
    ts.add_argument('-s', '--SeriesName', type=str, action='append', default=[], help="Target a specific series inside a show library based on it's name; allowed to give argument multiple times")
    # autopep8: on

    args = parser.parse_args()

    keywords_to_genre(
        ssn, keywords=args.Keyword,
        library_names=args.LibraryName,
        movie_names=args.MovieName,
        series_names=args.SeriesName,
        skip_locked=args.SkipLocked,
        use_label=args.UseLabel
    )
