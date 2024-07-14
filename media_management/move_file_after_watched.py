#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The use case of this script is the following:
    After watching a movie, move the movie file from one folder to another.

Note:
    When the file is directly in nthe source folder, the file + .srt, .ass and .nfo files
    with the same name will be moved. When the file is in it's own sub-folder in the source
    folder, the whole folder will be moved.

    /source/movie.{ext, srt, ass, nfo} -> /target/movie.{ext, srt, ass, nfo}
    /source/movie/* -> /target/movie/*

Requirements (python3 -m pip install [requirement]):
    requests
    websocket-client
    PlexAPI

Setup:
    1. Fill the variables below.
    2. Run the script in a terminal/shell with the "-h" flag to learn more about the parameters.
        python3 move_file_after_watched.py -h
        or
        python move_file_after_watched.py -h
    3. Run this script continuously. As long as it's running, it will be handling movies.
"""

import logging
from os import getenv, makedirs
from os.path import abspath, basename, dirname, isfile, join, relpath, splitext
from shutil import move
from time import sleep
from typing import TYPE_CHECKING, Any, Callable, Mapping

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
logging_level = logging.INFO
PSS = "PlaySessionStateNotification"


def prep_process(
    ssn: 'Session',
    source_folder: str,
    target_folder: str
) -> Callable[[Mapping[str, Any]], None]:
    def _process(data: Mapping[str, Any]) -> None:
        if PSS not in data:
            return

        if data[PSS][0]["state"] != "stopped":
            return

        media_output: Mapping[str, Any] = ssn.get(
            f"{base_url}/library/metadata/{data[PSS][0]['ratingKey']}"
        ).json()["MediaContainer"].get("Metadata", [{}])[0]
        if not media_output:
            return

        if media_output["type"] != "movie":
            return

        if "viewOffset" in media_output:
            return

        # Stream,
        # that has stopped because media has finished,
        # where media was a movie that has metadata

        for media in media_output.get("Media", []):
            for part in media["Part"]:
                if not part["file"].startswith(source_folder):
                    continue

                if dirname(part["file"]) == source_folder:
                    # File in source folder
                    for extension in (
                        splitext(part["file"])[1], ".srt", ".ass", ".nfo"
                    ):

                        source = splitext(part["file"])[0] + extension
                        if not isfile(source):
                            continue

                        target = join(target_folder, basename(source))
                        move(source, target)
                        logging.info(f"Moved {source} to {target}")

                else:
                    # File in sub-folder, move folder
                    dest_folder = join(
                        target_folder,
                        relpath(
                            dirname(part["file"]),
                            source_folder
                        )
                    )
                    makedirs(dirname(dest_folder), exist_ok=True)
                    move(dirname(part["file"]), dest_folder)
                    logging.info(
                        f"Moved {dirname(part['file'])} to {dest_folder}"
                    )

        return

    return _process


def move_file_after_watched(
    ssn: 'Session', plex: 'PlexServer',
    source_folder: str, target_folder: str
) -> None:
    """After watching a movie, move the movie file from one folder to another.

    Args:
        ssn (Session): The plex requests session to fetch with.
        plex (PlexServer): The plex session to use for the websocket connection.
        source_folder (str): The source folder to move files from.
        target_folder (str): The target folder to move files to.

    Raises:
        ValueError: Source folder and target folder are the same folder.
    """
    source_folder = abspath(source_folder)
    target_folder = abspath(target_folder)
    if source_folder == target_folder:
        raise ValueError(
            "Source folder and target folder cannot be the same folder")

    listener = plex.startAlertListener(callback=prep_process(
        ssn,
        source_folder,
        target_folder
    ))
    logging.info('Handling movie streams...')

    try:
        while sleep(5) is None: # type: ignore
            pass
    except KeyboardInterrupt:
        logging.info('Shutting down')
        listener.stop()

    return


if __name__ == "__main__":
    from argparse import ArgumentParser

    from plexapi.server import PlexServer
    from requests import Session

    # Setup vars
    ssn = Session()
    ssn.headers.update({'Accept': 'application/json'})
    ssn.params.update({'X-Plex-Token': plex_api_token}) # type: ignore

    plex = PlexServer(base_url, plex_api_token)

    # Setup logging
    logging.basicConfig(
        level=logging_level,
        format='[%(asctime)s][%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Setup arg parsing
    # autopep8: off
    parser = ArgumentParser(description="After watching a movie, move the movie file from one folder to another.")

    parser.add_argument('-S', '--SourceFolder', type=str, required=True, help="Folder from which movie files will be moved")
    parser.add_argument('-T', '--TargetFolder', type=str, required=True, help="Folder to which movie files will be moved")
    # autopep8: on

    args = parser.parse_args()

    try:
        move_file_after_watched(
            ssn, plex,
            args.SourceFolder, args.TargetFolder
        )

    except ValueError as e:
        parser.error(e.args[0])
