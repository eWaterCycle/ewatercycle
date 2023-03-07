"""Generate lisvap files to be used for lisflood.

example:
from .lisvap import create_lisvap_config, lisvap
config_file = create_lisvap_config(
    parameterset_dir,
    forcing_dir,
    forcing_name,
    lisvap_config,
    mask_map,
    start_time,
    end_time,
    forcing_files,
    )
lisvap(
    version,
    parameterset_dir,
    forcing_dir,
    mask_map,
    config_file,
    )
"""

import os
import subprocess
from typing import Dict, Tuple

from ewatercycle import CFG
from ewatercycle.parametersetdb.config import XmlConfig

from ..config._lisflood_versions import get_docker_image, get_singularity_image
from ..util import get_time


def lisvap(
    version: str,
    parameterset_dir: str,
    forcing_dir: str,
    mask_map: str,
    config_file: str,
) -> Tuple[int, bytes, bytes]:
    """Run lisvap to generate evaporation forcing files

    Returns:
        Tuple with exit code, stdout and stderr
    """
    mount_points = (
        parameterset_dir,
        mask_map,
        forcing_dir,
    )

    if CFG["container_engine"].lower() == "singularity":
        image = get_singularity_image(version, CFG["singularity_dir"])
        args = [
            "singularity",
            "exec",
            "--bind",
            ",".join([f"{mp}:{mp}" for mp in mount_points]),
            "--pwd",
            f"{forcing_dir}",
            image,
        ]
    elif CFG["container_engine"].lower() == "docker":
        image = get_docker_image(version)
        args = [
            "docker",
            "run",
            "-ti",
            "--volume",
            ",".join(f"{mp}:{mp}" for mp in mount_points),
            "--pwd",
            f"{forcing_dir}",
            image,
        ]
    else:
        raise ValueError(
            f"Unknown container technology in CFG: {CFG['container_engine']}"
        )

    args += ["python3", "/opt/Lisvap/src/lisvap1.py", config_file]
    container = subprocess.Popen(
        args, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    exit_code = container.wait()
    stdout, stderr = container.communicate()
    if exit_code != 0:
        raise subprocess.CalledProcessError(
            returncode=exit_code, cmd=args, stderr=stderr, output=stdout
        )

    return exit_code, stdout, stderr


def create_lisvap_config(
    parameterset_dir: str,
    forcing_dir: str,
    forcing_name: str,
    config_template: str,
    mask_map: str,
    start_time: str,
    end_time: str,
    forcing_files: Dict,
) -> str:
    """
    Create lisvap setting file.

    """
    cfg = XmlConfig(config_template)
    # Make a dictionary for settings
    settings = {
        "CalendarDayStart": get_time(start_time).strftime("%d/%m/%Y %H:%M"),
        "StepStart": get_time(start_time).strftime("%d/%m/%Y %H:%M"),
        "StepEnd": get_time(end_time).strftime("%d/%m/%Y %H:%M"),
        "PathOut": forcing_dir,
        "PathBaseMapsIn": f"{parameterset_dir}/maps_netcdf",
        "MaskMap": mask_map.replace(".nc", ""),
        "PathMeteoIn": forcing_dir,
    }

    for textvar in cfg.config.iter("textvar"):
        textvar_name = textvar.attrib["name"]

        # general settings
        for key, value in settings.items():
            if key in textvar_name:
                textvar.set("value", value)

        # lisvap input files
        # mapping lisvap input varnames to cmor varnames
        INPUT_NAMES = {
            "TAvgMaps": "tas",
            "TMaxMaps": "tasmax",
            "TMinMaps": "tasmin",
            "EActMaps": "e",
            "WindMaps": "sfcWind",
            "RgdMaps": "rsds",
        }
        for lisvap_var, cmor_var in INPUT_NAMES.items():
            if lisvap_var in textvar_name:
                filename = forcing_files[cmor_var].replace(".nc", "")
                textvar.set(
                    "value",
                    f"$(PathMeteoIn)/{filename}",
                )

        # lisvap output files
        # MapsName: {prefix_name, prefix}
        MAPS_PREFIXES = {
            "E0Maps": {"name": "PrefixE0", "value": "e0"},
            "ES0Maps": {"name": "PrefixES0", "value": "es0"},
            "ET0Maps": {"name": "PrefixET0", "value": "et0"},
        }
        for prefix in MAPS_PREFIXES.values():
            if prefix["name"] in textvar_name:
                filename = forcing_files[prefix["value"]].replace(".nc", "")
                textvar.set(
                    "value",
                    f"{filename}",
                )

    # Write to new setting file
    lisvap_file = f"{forcing_dir}/lisvap_{forcing_name}_setting.xml"
    cfg.save(lisvap_file)
    return lisvap_file
