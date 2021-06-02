"""Generate lisvap files to be used for lisflood.

example:
from .lisvap import create_lisvap_config, run_lisvap
parameterset = LisfloodParameterSet(
                PathRoot=root,
                MaskMap=mask_dir / 'model_mask',
                config_template=root / 'settings_lat_lon-Run.xml',
            )
config_file = create_lisvap_config(parameterset, start_time, end_time, directory, forcing_files)
run_lisvap(version, config_file, parameterset, directory)
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Tuple

from ewatercycle import CFG
from ewatercycle.models.lisflood import LisfloodParameterSet, XmlConfig
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

def run_lisvap(version:str, config_file:str, parameterset: LisfloodParameterSet, directory:Path) -> Tuple[int, bytes, bytes]:
    """Run lisvap to generate evaporation input files

    Args:
        forcing: Path to forcing data

    Returns:
        Tuple with exit code, stdout and stderr
    """
    mount_points = {
        f'{parameterset.PathRoot}': '/data/lisflood_input',
        f'{parameterset.MaskMap}': '/data/model_mask.nc',
        f'{directory}': '/data/forcing',
        f'{directory}': '/output',
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

    lisvap_filename = Path(config_file).name
    args += ['python3', '/opt/Lisvap/src/lisvap1.py', f"/output/{lisvap_filename}"]
    container = subprocess.Popen(args, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exit_code = container.wait()
    stdout, stderr = container.communicate()
    return exit_code, stdout, stderr


def create_lisvap_config(parameterset:LisfloodParameterSet, start_time:str, end_time:str, directory:Path, forcing_files:Dict[str, str]) -> str:
    """Update lisvap setting file"""
    cfg = XmlConfig(parameterset.config_template)
    # Make a dictionary for settings
    maps = "/data/lisflood_input/maps_netcdf"
    start = get_time(start_time)
    end = get_time(end_time)
    timestamp = f"{start.year}_{end.year}"
    settings = {
        "CalendarDayStart": start.strftime("%d/%m/%Y 00:00"),
        "StepStart": start.strftime("%d/%m/%Y 00:00"),
        "StepEnd": end.strftime("%d/%m/%Y 00:00"),
        "PathOut": "/output",
        "PathBaseMapsIn": maps,
        "MaskMap": "/data/model_mask",
        "PathMeteoIn": "/data/forcing",
    }

    # Mapping lisvap input varnames to cmor varnames
    INPUT_NAMES = {
        'TAvgMaps': 'tas',
        'TMaxMaps': 'tasmax',
        'TMinMaps': 'tasmin',
        'EActMaps': 'e',
        'WindMaps': 'sfcWind',
        'RgdMaps': 'rsds',
    }
    for textvar in cfg.config.iter("textvar"):
        textvar_name = textvar.attrib["name"]

        # general settings
        for key, value in settings.items():
            if key in textvar_name:
                textvar.set("value", value)

        # lisvap input files
        for lisvap_var, cmor_var in INPUT_NAMES.items():
            if lisvap_var in textvar_name:
                filename = forcing_files[cmor_var]
                textvar.set(
                    "value", f"$(PathMeteoIn)/{filename}",
                )

        # lisvap output files
        maps_prefixes = {
            'E0Maps': {'name': 'PrefixE0', 'value': 'e0'},
            'ES0Maps': {'name': 'PrefixES0', 'value': 'es0'},
            'ET0Maps': {'name': 'PrefixET0', 'value': 'et0'},
        }
        for prefix in maps_prefixes.values():
            if prefix['name'] in textvar_name:
                textvar.set(
                    "value",
                    f"lisflood_{prefix['value']}_{timestamp}",
                )

    # Write to new setting file
    lisvap_file = f"{directory}/lisvap_setting.xml"
    cfg.save(lisvap_file)
    return lisvap_file
