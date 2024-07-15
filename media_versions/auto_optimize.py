#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Optimize the targeted media if it isn't already.

Requirements (python3 -m pip install [requirement]):
    requests
    PlexAPI

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 auto_optimize.py -h
        or
        python auto_optimize.py -h

Examples:
    --Profile Mobile --Limit 20 --AllMovie

        Optimize the first 20 movies that haven't been optimized
        with the "Mobile" profile yet.

    --Profile "Original Quality" --Library "Tv-series" --SeriesName "Breaking Bad"

        Optimize all episodes of "Breaking Bad" in the "Tv-series" library
        with the "Original Quality" profile if they haven't already.
"""

from dataclasses import dataclass, field
from os import getenv
from typing import TYPE_CHECKING, Any, Dict, Generator, List

if TYPE_CHECKING:
    from plexapi.server import PlexServer
    from requests import Session

# ===== FILL THESE VARIABLES =====
plex_base_url = ''
plex_api_token = ''
# ================================

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
base_url = plex_base_url.rstrip('/')

profile_to_id = {
    'Mobile': 1,
    'TV': 2,
    'Original Quality': 3
}


@dataclass
class LibraryFilter:
    all: bool = False
    all_movie: bool = False
    all_show: bool = False
    libraries: List[str] = field(default_factory=lambda: [])
    movies: List[str] = field(default_factory=lambda: [])
    series: List[str] = field(default_factory=lambda: [])
    season_numbers: List[int] = field(default_factory=lambda: [])
    episode_numbers: List[int] = field(default_factory=lambda: [])

    def __post_init__(self):
        self.content_specifiers = (
            self.libraries,
            self.movies,
            self.series, self.season_numbers, self.episode_numbers
        )
        self.lib_specifiers = (
            self.all_movie, self.all_show
        )

        if self.all:
            if (
                any(self.content_specifiers)
                or True in self.lib_specifiers
            ):
                raise ValueError(
                    "Can't combine the 'all' target specifier with any other target specifier")

        else:
            if True not in self.lib_specifiers and not self.libraries:
                raise ValueError(
                    "Either have to select all libraries of a type or supply library names")

            if len(self.series) > 1:
                if self.season_numbers:
                    # Season numbers with multiple series
                    raise ValueError(
                        "Can't give season numbers for multiple series")

                elif self.episode_numbers:
                    # Episode numbers with multiple series
                    raise ValueError(
                        "Can't give episode numbers for multiple series")

            elif len(self.series) == 1:
                if self.episode_numbers:
                    if not self.season_numbers:
                        # Episode numbers without a season
                        raise ValueError(
                            "Can't give episode numbers without specifying a season number")

                    elif len(self.season_numbers) > 1:
                        # Episode numbers with multiple seasons
                        raise ValueError(
                            "Can't give episode numbers with multiple seasons")

            else:
                # No series specified
                if self.season_numbers:
                    # Season numbers but no series
                    raise ValueError(
                        "Can't give season numbers without specifying a series")

                elif self.episode_numbers:
                    # Episode numbers but no series
                    raise ValueError(
                        "Can't give episode numbers without specifying a series")

        return


def _get_library_entries(
    ssn: 'Session',
    library_filter: LibraryFilter
) -> Generator[Dict[str, Any], Any, Any]:
    """Get library entries to iterate over.

    Args:
        ssn (Session): The plex requests session to fetch with.
        library_filter (LibraryFilter): The filters to apply to the media.

    Yields:
        Generator[Dict[str, Any], Any, Any]: The resulting media information.
    """
    lf = library_filter

    sections: List[dict] = ssn.get(
        f'{base_url}/library/sections'
    ).json()['MediaContainer'].get('Directory', [])

    for lib in sections:
        if not (
            lib['type'] in ('movie', 'show')
            and
                lf.all
                or lf.all_movie and lib['type'] == 'movie'
                or lf.all_show and lib['type'] == 'show'
                or lf.libraries and lib['title'] in lf.libraries
        ):
            continue

        print(lib['title'])
        lib_output: List[dict] = ssn.get(
            f'{base_url}/library/sections/{lib["key"]}/all'
        ).json()['MediaContainer'].get('Metadata', [])

        if lib['type'] == 'movie':
            for movie in lib_output:
                if lf.movies and not movie['title'] in lf.movies:
                    continue

                print(f'    {movie["title"]}')
                yield movie

        elif lib['type'] == 'show':
            for show in lib_output:
                if lf.series and not show['title'] in lf.series:
                    continue

                print(f'    {show["title"]}')
                show_output: List[dict] = ssn.get(
                    f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves'
                ).json()['MediaContainer'].get('Metadata', [])

                for episode in show_output:
                    if (
                        lf.season_numbers
                        and not episode['parentIndex'] in lf.season_numbers
                    ):
                        continue

                    if (
                        lf.episode_numbers
                        and not episode['index'] in lf.episode_numbers
                    ):
                        continue

                    print(
                        f'        S{episode["parentIndex"]}E{episode["index"]}')
                    yield episode
    return


def _optimize_check(media_info: Dict[str, Any], profile: str) -> bool:
    """Check if a certain media has been optimized with a profile.

    Args:
        media_info (Dict[str, Any]): The info of the media to check.
        profile (str): The profile to test against.

    Returns:
        bool: Whether or not the media has an optimized version
        with the given profile.
    """
    for media in media_info['Media']:
        for part in media['Part']:
            if profile in ('Mobile', 'TV'):
                if f'/Optimized for {profile}/' in part['file']:
                    return True
            elif profile == 'Original Quality':
                if f'/{profile}/' in part['file']:
                    return True
    return False


def auto_optimize(
    ssn: 'Session',
    plex: 'PlexServer',
    profile: str,
    library_filter: LibraryFilter,
    limit: int = -1
) -> List[int]:
    """Optimize the targeted media if it isn't already.

    Args:
        ssn (Session): The plex requests session to fetch with.
        plex (PlexServer): The plex instance to optimize with.
        profile (str): The optimization profile.
        library_filter (LibraryFilter): The filter to apply to the media.
        limit (int, optional): The max amount of media to optimize in one run.
            Defaults to -1.

    Raises:
        ValueError: Invalid profile.

    Returns:
        List[int]: List of media rating keys that were processed.
    """
    result_json = []
    counter = 0

    if profile not in profile_to_id:
        raise ValueError("Invalid profile")

    for media in _get_library_entries(ssn, library_filter):
        if limit >= 0 and counter == limit:
            print('Limit reached')
            return result_json

        if _optimize_check(media, profile):
            continue

        if media['type'] == 'movie':
            print(f'        Not optimized for {profile}; optimizing')
        else:
            print(f'            Not optimized for {profile}; optimizing')

        plex.fetchItem(media['ratingKey']).optimize(
            locationID=-1,
            targetTagID=profile_to_id[profile]
        )
        result_json.append(media['ratingKey'])
        counter += 1

    return result_json


if __name__ == '__main__':
    from argparse import ArgumentParser

    from plexapi.server import PlexServer
    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Optimize the targeted media if it isn't already.")
    parser.add_argument('-P', '--Profile', type=str, choices=list(profile_to_id.keys()), required=True, help="The optimization profile")
    parser.add_argument('-L', '--Limit', type=int, default=-1, help="Maximum amount of media that the script is allowed to send to the queue")

    ts = parser.add_argument_group(title="Target Selectors")
    ts.add_argument('-a','--All', action='store_true', help="Target every media item in every library (use with care!)")
    ts.add_argument('--AllMovie', action='store_true', help="Target all movie libraries")
    ts.add_argument('--AllShow', action='store_true', help="Target all show libraries")

    ts.add_argument('-l', '--LibraryName', type=str, action='append', default=[], help="Name of target library; allowed to give argument multiple times")
    ts.add_argument('-m', '--MovieName', type=str, action='append', default=[], help="Target a specific movie inside a movie library based on it's name; allowed to give argument multiple times")
    ts.add_argument('-s', '--SeriesName', type=str, action='append', default=[], help="Target a specific series inside a show library based on it's name; allowed to give argument multiple times")
    ts.add_argument('-S', '--SeasonNumber', type=int, action='append', default=[], help="Target a specific season inside the targeted series based on it's number (only accepted when -s is given exactly once) (specials is 0); allowed to give argument multiple times")
    ts.add_argument('-e', '--EpisodeNumber', type=int, action='append', default=[], help="Target a specific episode inside the targeted season based on it's number (only accepted when -S is given exactly once); allowed to give argument multiple times")
    # autopep8: on

    args = parser.parse_args()

    plex = PlexServer(base_url, plex_api_token)
    try:
        lf = LibraryFilter(
            all=args.All,
            all_movie=args.AllMovie,
            all_show=args.AllShow,
            libraries=args.LibraryName,
            movies=args.MovieName,
            series=args.SeriesName,
            season_numbers=args.SeasonNumber,
            episode_numbers=args.EpisodeNumber
        )

    except ValueError as e:
        parser.error(e.args[0])

    auto_optimize(
        ssn=ssn,
        plex=plex,
        profile=args.Profile,
        library_filter=lf,
        limit=args.Limit
    )
