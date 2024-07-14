#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    Edit the intro and credit markers of plex media.
    Requires script to be run with root (a.k.a. administrator) privileges.

Setup:
    1. Fill the variable below.
        You can find the default location of your plex data directory here:
        https://support.plex.tv/articles/202915258-where-is-the-plex-media-server-data-directory-located/
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 intro_marker_editor.py -h
        or
        python intro_marker_editor.py -h

Examples:
    --Action list --LibraryName "Tv-series" --SeriesName "Peaky Blinders" --SeasonNumber 1

        List all intros and credits for the episodes of season 1 of the show "Peaky Blinders"
        in the library "Tv-series"

    -a add -l "Films" -m "6 Underground" -t credits -B 121:43 -E 124:02

        Add a credit marker to the movie "6 Underground" in the library "Films".
        The credit marker starts at 121:43 (= 2:01:43) and ends at 124:02 (= 2:04:02).

    -a shift -l "Tv-series" -s "Initial D" -O "-2"

        Shift the markers for all episodes of the series "Initial D" in the library "Tv-series".
        Shift all markers two seconds back (-2 seconds forwards).

    -a edit -n 276942 -B 00:00 -E 01:00

        Edit the marker with marker_number "276942". You can find the marker number of any
        marker in the output when using the "list" action.
        Change the start of the marker to 00:00 and the end to 01:00.

    -a remove -n 574745

        Delete the marker with marker_number "574745". You can find the marker number of any
        marker in the output when using the "list" action.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from json import dumps
from os import getenv
from os.path import isdir, isfile, join
from sqlite3 import Cursor, OperationalError, Row, connect
from typing import List, Literal, Union

# ===== FILL THIS VARIABLE =====
plex_data_directory = '/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/'
# ================================

# Environmental Variables
plex_data_directory = getenv('plex_data_directory', plex_data_directory)


class Action(Enum):
    ADD = 'add'
    LIST = 'list'
    REMOVE = 'remove'
    EDIT = 'edit'
    SHIFT = 'shift'


@dataclass
class LibraryFilter:
    library: str
    movie: Union[str, None] = None
    series: Union[str, None] = None
    season_number: Union[int, None] = None
    episode_number: Union[int, None] = None

    def __post_init__(self):
        if (
            self.series is None
            and self.season_number is not None
        ):
            raise ValueError(
                "Can't give season number without specifying a series")

        if (
            self.season_number is None
            and self.episode_number is not None
        ):
            raise ValueError(
                "Can't give episode number without specifying a season number")

        return


@dataclass
class MarkerOption:
    marker_number: Union[int, None] = None
    marker_type: Union[Literal['intro'], Literal['credits'], None] = None
    marker_start: Union[str, None] = None
    marker_end: Union[str, None] = None
    marker_offset: Union[int, None] = None

    def __post_init__(self):
        if self.marker_start is not None:
            try:
                if ':' in self.marker_start:
                    split_time = self.marker_start.split(':')
                    self.marker_start_converted = (
                        int(split_time[0]) * 60000
                        + int(split_time[1]) * 1000
                    )
                else:
                    self.marker_start_converted = int(self.marker_start)
            except ValueError:
                raise ValueError(
                    f"Invalid value for marker start: {self.marker_start}")

        if self.marker_end is not None:
            try:
                if ':' in self.marker_end:
                    split_time = self.marker_end.split(':')
                    self.marker_end_converted = (
                        int(split_time[0]) * 60000
                        + int(split_time[1]) * 1000
                    )
                else:
                    self.marker_end_converted = int(self.marker_end)
            except ValueError:
                raise ValueError(
                    f"Invalid value for marker end: {self.marker_end}")

        if None not in (self.marker_start, self.marker_end):
            if self.marker_end_converted < self.marker_start_converted:
                raise ValueError("End of marker is before start of marker")

        return


def _get_episodes(
    cursor: Cursor, series_id: int, library_filter: LibraryFilter
) -> List[dict]:
    """Get the episodes of a series based on the library filter.

    Args:
        cursor (Cursor): The cursor to make the db commands with in the plex db.
        series_id (int): The rating key of the series to get the episodes of.
        library_filter (LibraryFilter): The library filter to apply.

    Raises:
        ValueError: Series doesn't have any episodes.
        ValueError: Season not found.
        ValueError: Episode not found.

    Returns:
        List[dict]: The list of episodes.
    """
    lf = library_filter

    if lf.season_number is None:
        # Get all episodes in series
        cursor.execute("""
            WITH seasons
            AS (
                SELECT
                    id,
                    `index` AS season_number
                FROM metadata_items
                WHERE
                    metadata_type = 3
                    AND parent_id = ?
                )
            SELECT
                title,
                season_number,
                `index` AS episode_number,
                mi.id
            FROM metadata_items mi
            INNER JOIN seasons s
            ON mi.parent_id = s.id
            WHERE metadata_type = 4
            ORDER BY s.season_number, `index`;
        """, (series_id,))
        episode_info = list(map(dict, cursor))
        if not episode_info:
            raise ValueError("Series is empty")

    elif lf.episode_number is None:
        # Get all episodes in a season of the series
        cursor.execute("""
            WITH season
            AS (
                SELECT
                    id,
                    `index` AS season_number
                FROM metadata_items
                WHERE
                    metadata_type = 3
                    AND parent_id = ?
                    AND `index` = ?
                )
            SELECT
                title,
                season_number,
                `index` AS episode_number,
                mi.id
            FROM metadata_items mi
            INNER JOIN season s
            ON mi.parent_id = s.id
            WHERE metadata_type = 4
            ORDER BY `index`;
        """, (series_id, lf.season_number))
        episode_info = list(map(dict, cursor))
        if not episode_info:
            raise ValueError("Season not found")

    else:
        # Get a specific episode of the series
        cursor.execute("""
            WITH season
            AS (
                SELECT
                    id,
                    `index` AS season_number
                FROM metadata_items
                WHERE
                    metadata_type = 3
                    AND parent_id = ?
                    AND `index` = ?
                )
            SELECT
                title,
                season_number,
                `index` AS episode_number,
                mi.id
            FROM metadata_items mi
            INNER JOIN season s
            ON mi.parent_id = s.id
            WHERE
                metadata_type = 4
                AND `index` = ?;
        """, (series_id, lf.season_number, lf.episode_number))
        episode_info = list(map(dict, cursor))
        if not episode_info:
            raise ValueError("Episode not found")

    return episode_info


def _get_media(cursor: Cursor, library_filter: LibraryFilter) -> List[dict]:
    """Get the media that matches the library filter.

    Args:
        cursor (Cursor): The cursor to make the db commands with in the plex db.
        library_filter (LibraryFilter): The filter to apply.

    Raises:
        ValueError: Library not found or invalid.
        ValueError: Movie not found.
        ValueError: Series not found.

    Returns:
        List[dict]: The list of media.
    """
    lf = library_filter

    # Get library id and series id
    cursor.execute("""
        SELECT id
        FROM library_sections
        WHERE
            name = ?
            AND (section_type = 1
                OR section_type = 2)
        LIMIT 1;
        """,
        (lf.library,)
    )
    lib_id = next(iter(cursor.fetchone() or []), None)
    if lib_id is None:
        raise ValueError("Library not found or not a movie/show library")

    media_info = []
    if lf.movie:
        cursor.execute("""
            SELECT title, id
            FROM metadata_items
            WHERE
                library_section_id = ?
                AND title = ?
            """,
            (lib_id, lf.movie)
        )
        media_info = list(map(dict, cursor))
        if not media_info:
            raise ValueError("Movie not found in library")

    elif lf.series:
        cursor.execute("""
            SELECT id
            FROM metadata_items
            WHERE
                library_section_id = ?
                AND title = ?
            """,
            (lib_id, lf.series)
        )
        series_id = next(iter(cursor.fetchone() or []), None)
        if series_id is None:
            raise ValueError("Series not found in library")

        media_info = _get_episodes(cursor, series_id, library_filter)

    return media_info


def _add_marker(
    cursor: Cursor,
    media_id: int, marker_option: MarkerOption
) -> None:
    """Add a marker for a media entry.

    Args:
        cursor (Cursor): The cursor to make the db commands with in the plex db.
        media_id (int): The rating key of the media to add to marker for.
        marker_option (MarkerOption): The marker options.
    """
    # Check for existing markers
    result = cursor.execute("""
        SELECT tag_id, `index`
        FROM taggings
        WHERE
            metadata_item_id = ?
            AND (text = 'intro'
                OR text = 'credits')
        ORDER BY `index` DESC
        LIMIT 1;
        """,
        (media_id,)
    ).fetchone()

    if result is None:
        # Media doesn't have marker yet
        cursor.execute("""
            SELECT
                (
                    SELECT tag_id AS main
                    FROM taggings
                    WHERE (text = 'intro'
                            OR text = 'credits')
                ),
                (
                    SELECT tag_id + 1 AS alt
                    FROM taggings
                    ORDER BY tag_id DESC
                    LIMIT 1
                );
            """
        )
        i = cursor.fetchone()
        result = [i[0] or i[1], 0]

    args = (
        media_id,
        result[0],
        result[1] + 1,
        marker_option.marker_type,
        marker_option.marker_start_converted,
        marker_option.marker_end_converted,
        '',
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'pv%3Aversion=5'
    )

    cursor.execute("""
        INSERT INTO taggings(
            metadata_item_id, tag_id, `index`,
            text,
            time_offset, end_time_offset,
            thumb_url, created_at,
            extra_data
        ) VALUES (
            ?, ?, ?,
            ?,
            ?, ?,
            ?, ?,
            ?
        );
        """,
        (
            media_id, result[0], result[1] + 1,
            marker_option.marker_type,
            marker_option.marker_start_converted,
            marker_option.marker_end_converted,
            '', datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'pv%3Aversion=5'
        )
    )
    return


def intro_marker_editor(
    action: Action,
    library_filter: LibraryFilter, marker_option: MarkerOption
) -> List[int]:
    """Edit the intro and credit markers of plex media.
    Editing requires script to be run with root (a.k.a. administrator) privileges.

    Args:
        action (Action): The type of action to do on the markers
        library_filter (LibraryFilter): The filter for the media to apply the action on.
        marker_option (MarkerOption): The options for the marker if needed.

    Raises:
        ValueError: Something wen't wrong. Check value of exception.

    Returns:
        List[int]: The rating keys of the media covered.
    """
    result_json = []
    lf = library_filter
    mo = marker_option

    # Check for illegal arg parsing
    if not isdir(plex_data_directory):
        raise ValueError('The plex data directory could not be found')
    db_location = join(
        plex_data_directory,
        'Plug-in Support',
        'Databases',
        'com.plexapp.plugins.library.db'
    )
    if not isfile(db_location):
        raise ValueError('The plex database file could not be found')

    if action == Action.ADD and not (
        (lf.episode_number is not None or lf.movie)
        and mo.marker_start
        and mo.marker_end
    ):
        raise ValueError(
            "Adding a marker requires a specific media entry and a starting and ending time")

    if action == Action.REMOVE and not mo.marker_number:
        raise ValueError("Removing a marker requires it's marker number")

    if action == Action.EDIT and not (
        mo.marker_number and mo.marker_start and mo.marker_end
    ):
        raise ValueError(
            "Editing a marker requires it's marker number, a starting time and an ending time")

    if action == Action.SHIFT and (
        (
            lf.episode_number is not None
            or lf.season_number is not None
            or lf.series
            or lf.movie
        )
        and mo.marker_offset is None
    ):
        raise ValueError(
            "Shifting a marker requires a specific media entry and an offset to apply")

    # Create connection to plex database
    db = connect(db_location, timeout=20.0)
    db.row_factory = Row
    cursor = db.cursor()

    if action in (Action.EDIT, Action.REMOVE):
        cursor.execute(
            "SELECT 1 FROM taggings WHERE id = ? LIMIT 1",
            (mo.marker_number,)
        )
        if cursor.fetchone() is None:
            raise ValueError('Marker number not found')

        if action == Action.EDIT:
            cursor.execute("""
                UPDATE taggings
                SET
                    time_offset = ?,
                    end_time_offset = ?
                WHERE id = ?;
                """,
                (
                    mo.marker_start_converted,
                    mo.marker_end_converted,
                    mo.marker_number
                )
            )

        elif action == Action.REMOVE:
            cursor.execute(
                "DELETE FROM taggings WHERE id = ?;",
                (mo.marker_number,)
            )

        db.commit()
        return result_json

    media_info = _get_media(cursor, lf)
    media_ids = [e['id'] for e in media_info]

    if action == Action.ADD:
        _add_marker(cursor, media_ids[0], mo)

    elif action == Action.SHIFT:
        for m_id in media_ids:
            cursor.execute("""
                UPDATE taggings
                SET
                    time_offset = time_offset + (? * 1000),
                    end_time_offset = end_time_offset + (? * 1000)
                WHERE
                      metadata_item_id = ?
                    AND (text = 'intro'
                        OR text = 'credits');
                """,
                (mo.marker_offset, mo.marker_offset, m_id)
            )

    db.commit()

    # Find the markers for each media item
    for media_item in media_info:
        cursor.execute(f"""
            SELECT
                text AS type,
                id AS marker_number,
                (
                    SELECT (
                        PRINTF('%02d',(time_offset / 1000 - time_offset / 1000 % 60) / 60))
                        || ':'
                        || PRINTF('%02d', (time_offset / 1000 % 60)
                    )
                ) AS marker_start,
                (
                    SELECT (
                        PRINTF('%02d', (end_time_offset / 1000 - end_time_offset / 1000 % 60) / 60))
                        || ':'
                        || PRINTF('%02d', (end_time_offset / 1000 % 60)
                    )
                ) AS marker_end
            FROM taggings
            WHERE
                metadata_item_id = ?
                AND (text = 'intro'
                    OR text = 'credits')
            ORDER BY marker_start;
            """,
            (media_item['id'],)
        )
        media_item['markers'] = list(map(dict, cursor))
        result_json.append(media_item.pop('id'))

    print(dumps(media_info, indent=4))

    return result_json


if __name__ == '__main__':
    from argparse import ArgumentParser

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="Edit the intro and credit markers of plex media. Requires script to be run with root (a.k.a. administrator) privileges.")

    parser.add_argument('-a', '--Action', choices=[n.lower() for n in Action._member_names_], required=True, help="The type of action you want to perform on the media or it's marker(s)")
    parser.add_argument('-n', '--MarkerNumber', type=int, default=None, help="EDIT/REMOVE ONLY: The number of the marker, shown when using '-a list'")
    parser.add_argument('-t', '--MarkerType', choices=('intro', 'credits'), default=None, help="ADD ONLY: The type of marker to add")
    parser.add_argument('-B', '--MarkerStart', type=str, default=None, help="ADD/EDIT ONLY: The starting time of the marker. Supported formats are miliseconds and MM:SS")
    parser.add_argument('-E', '--MarkerEnd', type=str, default=None, help="ADD/EDIT ONLY: The ending time of the marker. Supported formats are miliseconds and MM:SS")
    parser.add_argument('-O', '--MarkerOffset', type=int, default=None, help="SHIFT ONLY: The amount to shift the marker(s) in seconds (negative values supported using quotes e.g. \"-5\")")

    ts = parser.add_argument_group(title="Target Selectors")
    ts.add_argument('-l', '--LibraryName', type=str, default=None, help="LIST/ADD/SHIFT ONLY: Name of target library")
    ts.add_argument('-m', '--MovieName', type=str, default=None, help="LIST/ADD/SHIFT ONLY: Name of the movie in the movie library to target (only accepted when -l is a movie library)")
    ts.add_argument('-s', '--SeriesName', type=str, default=None, help="LIST/ADD/SHIFT ONLY: Name of the series in the series library to target (only accepted when -s is a series library)")
    ts.add_argument('-S', '--SeasonNumber', type=int, default=None, help="LIST/ADD/SHIFT ONLY: Target a specific season inside the targeted series based on it's number (only accepted when -s is given) (specials is 0)")
    ts.add_argument('-e', '--EpisodeNumber', type=int, default=None, help="LIST/ADD/SHIFT ONLY: Target a specific episode inside the targeted season based on it's number (only accepted when -S is given)")
    # autopep8: on

    args = parser.parse_args()

    try:
        lf = LibraryFilter(
            library=args.LibraryName,
            movie=args.MovieName,
            series=args.SeriesName,
            season_number=args.SeasonNumber,
            episode_number=args.EpisodeNumber
        )

        mo = MarkerOption(
            marker_number=args.MarkerNumber,
            marker_type=args.MarkerType,
            marker_start=args.MarkerStart,
            marker_end=args.MarkerEnd,
            marker_offset=args.MarkerOffset
        )

        intro_marker_editor(Action[args.Action.upper()], lf, mo)

    except ValueError as e:
        parser.error(e.args[0])

    except OperationalError:
        parser.error(
            "Run the script with root (a.k.a. administrator) privileges to make changes"
        )
