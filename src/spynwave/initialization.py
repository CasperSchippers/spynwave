"""
This file is part of the SpynWave package.
"""

import logging
import sys
import pkg_resources
from pathlib import Path
import shutil

from win32com.client import Dispatch


# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


def copy_files_to_local_folder(overwrite=True):
    log.info("Looking for files to copy.")
    source_dir = Path(pkg_resources.resource_filename('spynwave', 'data/'))

    # Find everything except python files and files starting with an underscore
    source_files = source_dir.glob("[!_]*[!py]")

    home = Path.home()
    target_dir = home / "spynwave"

    if not target_dir.exists():
        log.info(f"Target directory ({target_dir}) does not exist, creating directory.")
        target_dir.mkdir()

    log.info(f"Copying config and calibration data to {target_dir}.")
    for source_file in source_files:
        if (target_dir / source_file.name).is_file():

            if not overwrite:
                log.warning(f"! File {source_file.name} already exists in target directory; "
                            f"skipping file.")
                continue

            log.warning(f"! File {source_file.name} already exists in target directory; "
                        f"overwriting file.")

        log.info(f"- Copying {source_file.name}.")
        shutil.copy2(source_file, target_dir)


def create_shortcut():
    log.info("Creating shortcut on desktop.")
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        raise NotADirectoryError(f"Desktop folder ({desktop}) not found.")

    python_executable = Path(sys.executable)
    if not (python_executable.is_file() and python_executable.name == "python.exe"):
        raise FileNotFoundError(f"Could locate the python interpreter (found path = "
                                f"{python_executable})")

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(desktop / "spynwave.lnk"))
    shortcut.Targetpath = str(python_executable)
    shortcut.WorkingDirectory = str(desktop)
    shortcut.Arguments = '-m spynwave'
    # shortcut.IconLocation = icon
    shortcut.save()
    log.info("Created shortcut on desktop.")


def initialize_measurement_software():
    copy_files_to_local_folder()
    try:
        create_shortcut()
    except NotADirectoryError or FileNotFoundError as exc:
        log.error(f"Could not create shortcut, create one manually. Exception: {exc}")
