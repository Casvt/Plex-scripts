#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Up- or downgrade media if it falls under the defined rules.
    Radarr: script will change quality profile of movie and initiate search for it.
    Sonarr: script will change quality profile of series, initiate search for episodes and change quality profile of series back.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 auto_upgrade_media.py -h
        or
        python auto_upgrade_media.py -h

Examples:
    Coming Soon.
"""

from dataclasses import dataclass, field
from json import loads
from os import getenv
from time import time
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Set, Union

if TYPE_CHECKING:
    from requests import Session

# ===== FILL THESE VARIABLES =====
plex_base_url = ''
plex_api_token = ''

# Either radarr, sonarr or both
radarr_base_url = ''
radarr_api_token = ''

# Either radarr, sonarr or both
sonarr_base_url = ''
sonarr_api_token = ''

radarr_mapping = {
    # Define desired applied Radarr profile for each resolution
    # Leave a value empty to not up- or downgrade any further
    '480': '',
    '720': '',
    '1080': '',
    '4k': ''
}

sonarr_mapping = {
    # Define desired applied Sonarr profile for each resolution
    # Leave a value empty to not up- or downgrade any further
    '480': '',
    '720': '',
    '1080': '',
    '4k': ''
}

triggers = {
    # Define when to up- or downgrade media
    # Give -1 to never go to that resolution/don't use trigger
    # If you have multiple triggers setup, there is an AND correlation between them:
    #    That means that all triggers for a resolution must match in order for media to go to that resolution
    #    So you have to remove some of the triggers below to set it up how you want it
    'days_not_watched': {
        '480': 1095, # 1095 (3 years) days ago watched -> 480p
        '720': 365,  # 365-1094 days ago watched -> 720p
        '1080': 40,  # 40-364 days ago watched -> 1080p
        '4k': 0      # 0-39 days ago watched -> 4k
    },
    'viewcount': {
        '480': -1,
        '720': 1,   # 0-2 times watched -> 720p
        '1080': 3,  # 3-4 times watched -> 1080p
        '4k': 5     # 5+ times watched -> 4k
    },
    'inverted_viewcount': {
        '480': -1,
        '720': -1,
        '1080': 1,  # 1+ times watched -> 1080p
        '4k': 0     # 0 times watched -> 4k
    }
}
# ================================

# Environmental Variables
plex_base_url = getenv('plex_base_url', plex_base_url)
plex_api_token = getenv('plex_api_token', plex_api_token)
radarr_base_url = getenv(
    'radarr_base_url',
    radarr_base_url).rstrip('/') + '/api/v3'
radarr_api_token = getenv('radarr_api_token', radarr_api_token)
sonarr_base_url = getenv(
    'sonarr_base_url',
    sonarr_base_url).rstrip('/') + '/api/v3'
sonarr_api_token = getenv('sonarr_api_token', sonarr_api_token)
_radarr_mapping = getenv('radarr_mapping')
if _radarr_mapping:
    radarr_mapping: Dict[str, str] = loads(_radarr_mapping)
_sonarr_mapping = getenv('sonarr_mapping')
if _sonarr_mapping:
    sonarr_mapping: Dict[str, str] = loads(_sonarr_mapping)
_triggers = getenv('triggers')
if _triggers:
    triggers: Dict[str, Dict[str, int]] = loads(_triggers)
base_url = plex_base_url.rstrip('/')

resolutions = ('480', '720', '1080', '4k')


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


movie_cache: List[Dict[str, Any]] = []
series_cache: Dict[int, Dict[str, Any]] = {}
r_profiles_cache: List[Dict[str, Any]] = []
s_profiles_cache: List[Dict[str, Any]] = []


def _change_media(
    radarr_ssn: 'Session',
    sonarr_ssn: 'Session',
    media: Dict[str, Any],
    resolution: str
):
    filepath_current_file = (
        media
        .get('Media', [{}])[0]
        .get('Part', [{}])[0]
        .get('file')
    )
    if not filepath_current_file:
        return

    if media['type'] == 'movie':
        print(f'        Setting to {resolution}')

        if not movie_cache:
            movie_cache.extend(
                radarr_ssn.get(f'{radarr_base_url}/movie').json()
            )
        if not r_profiles_cache:
            r_profiles_cache.extend(
                radarr_ssn.get(f'{radarr_base_url}/qualityprofile').json()
            )

        # Find movie in radarr
        for movie in movie_cache:
            if movie.get('movieFile', {}).get('path') == filepath_current_file:
                movie_id = movie['id']
                break
        else:
            return

        # Find id of quality profile in radarr
        for profile in r_profiles_cache:
            if profile['name'] == radarr_mapping.get(resolution):
                profile_id = profile['id']
                break
        else:
            return

        radarr_ssn.put(
            f'{radarr_base_url}/movie/editor',
            json={
                'movieIds': [movie_id],
                'qualityProfileId': profile_id
            }
        )
        radarr_ssn.post(
            f'{radarr_base_url}/command',
            json={
                'movieIds': [movie_id],
                'name': 'MoviesSearch'
            }
        )

    elif media['type'] == 'episode':
        print(f'            Setting to {resolution}')

        if not s_profiles_cache:
            s_profiles_cache.extend(
                sonarr_ssn.get(f'{sonarr_base_url}/qualityprofile').json()
            )

        # Find episode in sonarr
        episode_search: Union[Dict[str, Any], None] = next(
            iter(
                sonarr_ssn.get(
                    f'{sonarr_base_url}/parse',
                    params={'path': filepath_current_file}
                ).json().get('episodes', [])
            ),
            None
        )
        if not episode_search:
            return
        series_id: int = episode_search['seriesId']

        if series_id not in series_cache:
            series_cache[series_id] = sonarr_ssn.get(
                f'{sonarr_base_url}/series/{series_id}'
            ).json()

        # Find id of quality profile in sonarr
        for profile in s_profiles_cache:
            if profile['name'] == sonarr_mapping.get(resolution):
                profile_id: int = profile['id']
                break
        else:
            return

        current_qp: int = series_cache[series_id]['qualityProfileId']
        series_cache[series_id]['qualityProfileId'] = profile_id
        sonarr_ssn.put(
            f'{sonarr_base_url}/series/{series_id}',
            json=series_cache[series_id]
        )
        sonarr_ssn.post(
            f'{sonarr_base_url}/command',
            json={
                'name': 'EpisodeSearch',
                'episodeIds': [episode_search['id']]
            }
        )
        series_cache[series_id]['qualityProfileId'] = current_qp
        sonarr_ssn.put(
            f'{sonarr_base_url}/series/{series_id}',
            json=series_cache[series_id]
        )

    return


def _process_media(
    radarr_ssn: 'Session',
    sonarr_ssn: 'Session',
    media: Dict[str, Any]
) -> None:
    current_time = time()
    desired_resolutions: Set[str] = set()
    current_resolution = (
        media
        .get('Media', [{}])[0]
        .get('videoResolution')
    )

    viewcount = media.get('viewCount', 0)
    days_not_watched: float = (
        (current_time - media.get('lastViewedAt', current_time + 1))
        /
        86400
    )

    if not current_resolution:
        return

    if 'days_not_watched' in triggers and days_not_watched >= 0:
        for resolution in resolutions:
            days = triggers['days_not_watched'].get(resolution, -1)
            if days_not_watched >= days > -1:
                # Found desired resolution based on days_not_watched
                desired_resolutions.add(resolution)
                break

    if 'viewcount' in triggers:
        for resolution in reversed(resolutions):
            views = triggers['viewcount'].get(resolution, -1)
            if viewcount >= views > -1:
                # Found desired resolution based on viewcount
                desired_resolutions.add(resolution)
                break

    if 'inverted_viewcount' in triggers:
        for resolution in resolutions:
            views = triggers['inverted_viewcount'].get(resolution, -1)
            if viewcount >= views > -1:
                # Found desired resolution based on inverted_viewcount
                desired_resolutions.add(resolution)
                break

    results = list(desired_resolutions)
    if len(results) != 1:
        return

    result = results[0]
    if (
        current_resolution != result
        and (
            (radarr_mapping if media['type'] == 'movie' else sonarr_mapping)
            .get(result) or ''
        ) != ''
    ):
        # Up- or downgrade media
        _change_media(
            radarr_ssn=radarr_ssn, sonarr_ssn=sonarr_ssn,
            media=media, resolution=result
        )

    return


def auto_upgrade_media(
    plex_ssn: 'Session',
    radarr_ssn: 'Session',
    sonarr_ssn: 'Session',
    library_filter: LibraryFilter
) -> List[int]:
    result_json = []

    radarr_enabled = radarr_base_url != '' and radarr_api_token != ''
    sonarr_enabled = sonarr_base_url != '' and sonarr_api_token != ''
    if not (radarr_enabled or sonarr_enabled):
        raise ValueError("Either Sonarr or Radarr needs to be set up")

    for media in _get_library_entries(plex_ssn, library_filter):
        if media['type'] == 'movie' and not radarr_enabled:
            continue
        if media['type'] == 'episode' and not sonarr_enabled:
            continue

        _process_media(radarr_ssn, sonarr_ssn, media)

        result_json.append(media['ratingKey'])

    return result_json


if __name__ == '__main__':
    from argparse import ArgumentParser

    from requests import Session

    # Setup vars
    plex_ssn = Session()
    plex_ssn.headers.update({'Accept': 'application/json'})
    plex_ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore
    radarr_ssn = Session()
    radarr_ssn.params.update({'apikey': radarr_api_token}) # type: ignore
    sonarr_ssn = Session()
    sonarr_ssn.params.update({'apikey': sonarr_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Up- or downgrade media if it falls under the defined rules.")

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

        auto_upgrade_media(
            plex_ssn, radarr_ssn, sonarr_ssn,
            library_filter=lf
        )

    except ValueError as e:
        parser.error(e.args[0])
