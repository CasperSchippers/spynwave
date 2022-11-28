"""
This file is part of the SpynWave package.
"""

import logging
import pkg_resources
from pathlib import Path
import shutil


# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


def copy_files_to_local_folder(overwrite=True):
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
        if not overwrite:
            if (target_dir / source_file.name).is_file():
                log.warning(f"! File {source_file.name} already exists in target directory.")
                continue

        log.info(f"- Copying {source_file.name}.")
        shutil.copy2(source_file, target_dir)


def initialize_measurement_software():
    copy_files_to_local_folder()

