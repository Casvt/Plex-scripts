#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    If targeted media falls under certain conditions, delete the file.

Warning:
    This script deletes media files if they match the rules set by you!
    I'm not responsible for any unintended loss of data.

Requirements (python3 -m pip install [requirement]):
    requests

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 recent_episode_maintainer.py -h
        or
        python recent_episode_maintainer.py -h

Examples:
    --MatchAll --Collection "Christopher Nolan Movies" --Resolution "<1080" --AllMovie

        Delete all movies that are part of the collection "Christopher Nolan Movies"
        and have a resolution of 1080p or lower.

    --Preview --Exclude "After*" --ViewCount ">2" --DaysAdded ">365" --AllMovie

        List all movies that have either been watched 2 or more times or have
        been added 365 days or more ago but that don't have a title that starts
        with "After".

    --RecentEpisodes 5 --Size ">400" -l "Tv-series" -s "The Legend of Korra" -s "Avatar: The Last Airbender"

        Delete all episodes of the series "The Legend of Korra" and "Avatar: The
        Last Airbender" from the "Tv-series" library except the last 5 of each.
        Episodes out of these 5 could still be deleted though, if they are 400 MB
        or larger in size.
"""

from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import filter as fnmatch_filter
from os import getenv
from time import time
from typing import (TYPE_CHECKING, Any, Callable, Dict,
                    Generator, List, Mapping, Union)

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

TMedia = Mapping[str, Any]
RESOLUTIONS = {
    "480": 1,
    "720": 2,
    "1080": 3,
    "2k": 4,
    "4k": 5,
    "6k": 6,
    "8k": 7
}
OPERATORS = {'<', '>', '='}


def exclude_media(exclude: List[str]) -> Callable[[TMedia], bool]:
    def op(media: TMedia) -> bool:
        return any((
            fnmatch_filter((media["title"],), pattern)
            for pattern in exclude
        )) # True if it should be excluded
    return op


extract_last_watch: Callable[[TMedia], Union[int, None]] = (
    lambda media: media.get("lastViewedAt")
)
extract_view_count: Callable[[TMedia], int] = (
    lambda media: media.get("viewCount", 0)
)
extract_added_at: Callable[[TMedia], Union[int, None]] = (
    lambda media: media.get("addedAt")
)
extract_size: Callable[[TMedia], Union[int, None]] = (
    lambda media: media
    .get("Media", [{}])[0]
    .get("Part", [{}])[0]
    .get("size")
)
extract_res: Callable[[TMedia], Union[int, None]] = (
    lambda media: RESOLUTIONS.get(
        media.get("Media", [{}])[0]
        .get("videoResolution")
    )
)
extract_bitrate: Callable[[TMedia], Union[int, None]] = (
    lambda media: media
    .get("Media", [{}])[0]
    .get("bitrate")
)
extract_added_date: Callable[[TMedia], Union[datetime, None]] = (
    lambda media:
        None
        if "addedAt" not in media else
        datetime.fromtimestamp(media["addedAt"])
)


def get_operator(
    extractor: Callable[[TMedia], Any],
    operator: str,
    value: Any
) -> Callable[[TMedia], bool]:
    if operator == '<':
        def op(media: TMedia) -> bool:
            v = extractor(media)
            if v is None:
                return False
            return v <= value

    elif operator == '>':
        def op(media: TMedia) -> bool:
            v = extractor(media)
            if v is None:
                return False
            return v >= value

    elif operator == '=':
        def op(media: TMedia) -> bool:
            v = extractor(media)
            if v is None:
                return False
            return v == value

    else:
        raise RuntimeError(f"Unknown operator: {operator}")

    return op


def prep_days_ago(
    extractor: Callable[[TMedia], Any],
    operator: str,
    value: int
) -> Callable[[TMedia], bool]:
    def check_days_ago(media: TMedia) -> bool:
        lw: Union[int, None] = extractor(media)
        if not lw:
            return False
        days_ago = (time() - lw) // 86400

        if operator == '<':
            return days_ago <= value
        elif operator == '>':
            return days_ago >= value
        elif operator == '=':
            return days_ago == value
        else:
            raise RuntimeError(f"Unknown operator: {operator}")

    return check_days_ago


RECENT_EPISODES: Dict[str, List[str]] = {}


def prep_recent_eps() -> Callable[[TMedia], bool]:
    def recent_eps(media: TMedia) -> bool:
        if media["type"] != "episode":
            return False
        return not media["ratingKey"] in RECENT_EPISODES[media["grandparentRatingKey"]]

    return recent_eps


def prep_field_check(
    field: str,
    value: str
) -> Callable[[TMedia], bool]:
    def field_check(media: TMedia) -> bool:
        if field not in media:
            return False

        tags = {f["tag"] for f in media[field]}
        return value in tags

    return field_check


@dataclass
class MediaFilter:
    match_all: bool
    exclude: List[str]
    recent_episodes: Union[int, None]
    last_watch: Union[str, None]
    view_count: Union[str, None]
    days_added: Union[str, None]
    date: Union[str, None]
    size: Union[str, None]
    resolution: Union[str, None]
    bitrate: Union[str, None]
    collection: Union[str, None]
    label: Union[str, None]

    def __post_init__(self) -> None:
        self.filters: List[Callable[[TMedia], bool]] = []

        self.check_exclude = None
        if self.exclude:
            self.check_exclude = exclude_media(self.exclude)

        if self.recent_episodes:
            self.filters.append(prep_recent_eps())

        if self.last_watch:
            op = self.last_watch[0]
            value = self.last_watch[1:]
            if op not in OPERATORS:
                raise ValueError("Invalid operator for last watch")
            if not value.isdigit():
                raise ValueError("Invalid number for last watch")

            self.filters.append(prep_days_ago(
                extract_last_watch,
                op,
                int(value)
            ))

        if self.view_count is not None:
            op = self.view_count[0]
            value = self.view_count[1:]
            if op not in OPERATORS:
                raise ValueError("Invalid operator for view count")
            if not value.isdigit():
                raise ValueError("Invalid number for view count")
            self.filters.append(get_operator(
                extract_view_count,
                op,
                int(value)
            ))

        if self.days_added is not None:
            op = self.days_added[0]
            value = self.days_added[1:]
            if op not in OPERATORS:
                raise ValueError("Invalid operator for days added")
            if not value.isdigit():
                raise ValueError("Invalid number for days added")

            self.filters.append(prep_days_ago(
                extract_added_at,
                op,
                int(value)
            ))

        if self.date is not None:
            op = self.date[0]
            value = self.date[1:]
            if op not in OPERATORS:
                raise ValueError("Invalid operator for date")
            try:
                value = datetime.strptime(value, "%d-%m-%Y")
            except ValueError:
                raise ValueError("Invalid date")

            self.filters.append(get_operator(
                extract_added_date,
                op,
                value
            ))

        if self.size is not None:
            op = self.size[0]
            value = self.size[1:]
            if op not in OPERATORS:
                raise ValueError("Invalid operator for size")
            if not value.isdigit():
                raise ValueError("Invalid number for size")
            self.filters.append(get_operator(
                extract_size,
                op,
                int(value) * 1_000_000
            ))

        if self.resolution is not None:
            op = self.resolution[0]
            value = self.resolution[1:]
            if op not in OPERATORS:
                raise ValueError("Invalid operator for resolution")
            if value not in RESOLUTIONS:
                raise ValueError("Invalid value for resolution")
            self.filters.append(get_operator(
                extract_res,
                op,
                RESOLUTIONS[value]
            ))

        if self.bitrate is not None:
            op = self.bitrate[0]
            value = self.bitrate[1:]
            if op not in OPERATORS:
                raise ValueError("Invalid operator for bitrate")
            if not value.isdigit():
                raise ValueError("Invalid number for bitrate")
            self.filters.append(get_operator(
                extract_bitrate,
                op,
                int(value)
            ))

        if self.collection is not None:
            self.filters.append(prep_field_check(
                "Collection",
                self.collection
            ))

        if self.label is not None:
            self.filters.append(prep_field_check(
                "Label",
                self.label
            ))

        return

    def validate(self, media: TMedia) -> bool:
        """Check if media passes filter.

        Args:
            media (TMedia): The media to check for.

        Returns:
            bool: If it should be deleted or not.
        """
        if self.check_exclude is not None and self.check_exclude(media):
            return False

        if self.match_all:
            return all((f(media) for f in self.filters))
        else:
            return any((f(media) for f in self.filters))


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
    library_filter: LibraryFilter,
    media_filter: MediaFilter
) -> Generator[TMedia, Any, Any]:
    """Get library entries to iterate over.

    Args:
        ssn (Session): The `requests.Session` to make the requests with.
        library_filter (LibraryFilter): The filters to apply.

    Yields:
        Generator[TMedia, Any, Any]: The resulting media information.
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
        lib_output: List[TMedia] = ssn.get(
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
                show_output: List[TMedia] = ssn.get(
                    f'{base_url}/library/metadata/{show["ratingKey"]}/allLeaves'
                ).json()['MediaContainer'].get('Metadata', [])

                if media_filter.recent_episodes is not None:
                    RECENT_EPISODES[show["ratingKey"]] = [
                        e["ratingKey"]
                        for e in show_output[-media_filter.recent_episodes:]
                    ]

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
                        f'      S{episode["parentIndex"]}E{episode["index"]}')
                    yield episode
    return


def recent_episode_maintainer(
    ssn: 'Session',
    library_filter: LibraryFilter,
    media_filter: MediaFilter,
    preview: bool = False
) -> List[int]:
    """If targeted media falls under certain conditions, delete the file.

    Args:
        ssn (Session): The plex requests session to fetch with.
        library_filter (LibraryFilter): The filter to apply to the media.
        media_filter (MediaFilter): The filter to select what media to delete.
        preview (bool, optional): Only list matching media instead of actually deleting it.
            Defaults to False.

    Returns:
        List[int]: List of media rating keys that were processed.
    """
    result_json = []

    for media in _get_library_entries(ssn, library_filter, media_filter):
        result_json.append(media["ratingKey"])
        if not media_filter.validate(media):
            continue

        if not preview:
            ssn.delete(
                f"{base_url}/library/metadata/{media['ratingKey']}"
            )
            term = "Deleted"
        else:
            term = "Targeted"

        if media["type"] == "episode":
            print(f"            {term}")
        else:
            print(f"        {term}")

    return result_json


if __name__ == '__main__':
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    # Setup arg parsing
    # autopep8: off
    epilog = """
-------------------------
EPILOG

The arguments that refer to this epilog, have special formatting for their value.

Prefixing the value with a "<" means that the value can be the given value or smaller. For example, giving --Size "<1000" means to delete media that has a size of 1000 MB or less.

Prefixing the value with a ">" means that the value can be the given value or bigger. For example, giving --LastWatch ">100" means to delete media that hasn't been watched for 100 days or more.

Prefixing the value with a "=" means that the value can only be the given value. For example, giving --Date "=7-5-2024" means to delete media that was added exactly on the 7th of May 2024.

Not giving a prefix will lead to an error. Make sure to surround your values with quotes, like is done in the examples.
"""

    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description="If targeted media falls under certain conditions, delete the file.",
        epilog=epilog
    )

    parser.add_argument('--Preview', action='store_true', help="Don't process the media that falls under the criteria, just list it")
    parser.add_argument('--MatchAll', action='store_true', help="Instead of the media having to match ANY of the criteria, it has to match ALL the criteria")
    parser.add_argument('--Exclude', type=str, action='append', default=[], help="If these terms are found in the title of the media, then skip the media; glob patterns supported; allowed to give argument multiple times")

    ct = parser.add_argument_group(title="Criteria")
    ct.add_argument('--RecentEpisodes', type=int, help="Only keep the latest x episodes of a series")
    ct.add_argument('--LastWatch', type=str, help="Remove media based on how many days ago it was viewed for the last time. SEE EPILOG FOR POSSIBLE VALUES.")
    ct.add_argument('--ViewCount', type=str, help="Remove media based on how many time it has been watched. SEE EPILOG FOR POSSIBLE VALUES.")
    ct.add_argument('--DaysAdded', type=str, help="Remove media based on how many days ago it was added. SEE EPILOG FOR POSSIBLE VALUES.")
    ct.add_argument('--Date', type=str, help="Remove media based on the date it was added. In format DD-MM-YYYY. SEE EPILOG FOR POSSIBLE VALUES.")
    ct.add_argument('--Size', type=str, help="Remove media based on it's file size in MB. SEE EPILOG FOR POSSIBLE VALUES.")
    ct.add_argument('--Resolution', type=str, help="Remove media based on it's video resolution. Allowed resolutions are 480, 720, 1080, 2k, 4k, 6k and 8k. SEE EPILOG FOR POSSIBLE VALUES.")
    ct.add_argument('--Bitrate', type=str, help="Remove media based on it's bitrate in kbps. SEE EPILOG FOR POSSIBLE VALUES.")
    ct.add_argument('--Collection', type=str, help="Remove media if it's part of the given collection")
    ct.add_argument('--Label', type=str, help="Remove media if it has the given label")

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

        mf = MediaFilter(
            match_all=args.MatchAll,
            exclude=args.Exclude,
            recent_episodes=args.RecentEpisodes,
            last_watch=args.LastWatch,
            view_count=args.ViewCount,
            days_added=args.DaysAdded,
            date=args.Date,
            size=args.Size,
            resolution=args.Resolution,
            bitrate=args.Bitrate,
            collection=args.Collection,
            label=args.Label
        )

    except ValueError as e:
        parser.error(e.args[0])

    recent_episode_maintainer(
        ssn, lf, mf, args.Preview
    )
