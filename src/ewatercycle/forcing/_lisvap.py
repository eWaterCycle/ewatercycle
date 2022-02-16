"""Generate lisvap files to be used for lisflood.

example:
from .lisvap import create_lisvap_config, run_lisvap
config_file = create_lisvap_config(parameterset, start_time, end_time, directory, forcing_files)
run_lisvap(version, config_file, parameterset, directory)
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple

from ewatercycle import CFG
from ..models.lisflood import XmlConfig
from ..util import get_time


def _set_docker_image(version):
    images = {
        '20.10': 'ewatercycle/lisflood-grpc4bmi:20.10'
    }
    return images[version]

def _set_singularity_image(version, singularity_dir: Path):
    images = {
        '20.10': 'ewatercycle-lisflood-grpc4bmi_20.10.sif'
    }
    return singularity_dir / images[version]

def lisvap(
    version: str,
    parameterset_dir: str,
    forcing_dir: str,
    mask_map: str,
    config_file: str,
    ) -> Tuple[int, bytes, bytes]:
    """Run lisvap to generate evaporation forcing files

    Args:
        forcing: Path to forcing data

    Returns:
        Tuple with exit code, stdout and stderr
    """
    mount_points = {
        f'{parameterset_dir}': f'{parameterset_dir}',
        f'{mask_map}': '/data/model_mask.nc',
        f'{forcing_dir}': f'{forcing_dir}',
        f'{forcing_dir}': f'{forcing_dir}',
    }

    if CFG['container_engine'].lower() == 'singularity':
        singularity_image = _set_singularity_image(version, CFG['singularity_dir'])
        args = [
            "singularity",
            "exec",
        ]
        args += ["--bind", ','.join([hp + ':' + ip for hp, ip in mount_points.items()])]
        args.append(singularity_image)

    elif CFG['container_engine'].lower() == 'docker':
        docker_image = _set_docker_image(version)
        args = [
            "docker",
            "run -ti",
        ]
        args += ["--volume", ','.join([hp + ':' + ip for hp, ip in mount_points.items()])]
        args.append(docker_image)

    else:
        raise ValueError(
            f"Unknown container technology in CFG: {CFG['container_engine']}"
        )

    args += ['python3', '/opt/Lisvap/src/lisvap1.py', f"{config_file}"]
    container = subprocess.Popen(args, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exit_code = container.wait()
    stdout, stderr = container.communicate()
    return exit_code, stdout, stderr


def create_lisvap_config(
    parameterset_dir: str,
    forcing_dir: str,
    forcing_name: str,
    mask_map: str,
    start_time: str,
    end_time: str
    ) -> str:
    """
    Create lisvap setting file.

    """
    config_template = f'{parameterset_dir}/settings_lisvap.xml'
    cfg = XmlConfig(config_template)
    # Make a dictionary for settings
    settings = {
        "CalendarDayStart": get_time(start_time).strftime("%d/%m/%Y %H:%M"),
        "StepStart": get_time(start_time).strftime("%d/%m/%Y %H:%M"),
        "StepEnd": get_time(end_time).strftime("%d/%m/%Y %H:%M"),
        "PathOut": forcing_dir,
        "PathBaseMapsIn": f'{parameterset_dir}/maps_netcdf',
        "MaskMap": mask_map.replace('.nc', ''),
        "PathMeteoIn": forcing_dir,
    }

    start_year = get_time(start_time).year
    end_year = get_time(end_time).year
    timestamp = f"{start_year}_{end_year}"

    for textvar in cfg.config.iter("textvar"):
        textvar_name = textvar.attrib["name"]

        # general settings
        for key, value in settings.items():
            if key in textvar_name:
                textvar.set("value", value)

        # lisvap input files
        # mapping lisvap input varnames to cmor varnames
        INPUT_NAMES = {
            'TAvgMaps': 'tas',
            'TMaxMaps': 'tasmax',
            'TMinMaps': 'tasmin',
            'EActMaps': 'e',
            'WindMaps': 'sfcWind',
            'RgdMaps': 'rsds',
        }
        for lisvap_var, cmor_var in INPUT_NAMES.items():
            if lisvap_var in textvar_name:
                filename = f"lisflood_{forcing_name}_{cmor_var}_{timestamp}"
                textvar.set(
                    "value", f"$(PathMeteoIn)/{filename}",
                )

        # lisvap output files
        # MapsName: {prefix_name, prefix}
        MAPS_PREFIXES = {
            'E0Maps': {'name': 'PrefixE0', 'value': 'e0'},
            'ES0Maps': {'name': 'PrefixES0', 'value': 'es0'},
            'ET0Maps': {'name': 'PrefixET0', 'value': 'et0'},
        }
        for prefix in MAPS_PREFIXES.values():
            if prefix['name'] in textvar_name:
                textvar.set(
                    "value",
                    f"lisflood_{forcing_name}_{prefix['value']}_{timestamp}",
                )

    # Write to new setting file
    lisvap_file = f"{forcing_dir}/lisvap_{forcing_name}_setting.xml"
    cfg.save(lisvap_file)
    return lisvap_file
