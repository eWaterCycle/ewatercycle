from ewatercycle.parametersetdb.config import AbstractConfig
import xml.etree.ElementTree as ET
from ewatercycle.models.abstract import AbstractModel
from grpc4bmi.bmi_client_singularity import BmiClientSingularity
from grpc4bmi.bmi_client_docker import BmiClientDocker
from ewatercycle import CFG
from os import PathLike
from typing import Tuple, Iterable, Any, Optional


input_dir = CFG.lisflood.input_dir
mask_dir = CFG.lisflood.mask_dir
forcing_dir = CFG.lisflood.forcing_dir
work_dir = CFG.lisflood.work_dir
lisflood_config_path = CFG.lisflood.settings_lisflood
lisvap_config_path = CFG.lisflood.settings_lisvap

# mapping lisvap input varnames to cmor varnames
INPUT_NAMES = {
    'TAvgMaps': 'tas',
    'TMaxMaps': 'tasmax',
    'TMinMaps': 'tasmin',
    'EActMaps': 'e',
    'WindMaps': 'sfcWind',
    'RgdMaps': 'rsds',
}

# LISFLOOD settings file reference maps prefixes
# MapsName: {prefix_name, prefix}
MAPS_PREFIXES = {
    'E0Maps': {'name': 'PrefixE0', 'value': 'e0'},
    'ES0Maps': {'name': 'PrefixES0', 'value': 'es0'},
    'ET0Maps': {'name': 'PrefixET0', 'value': 'et0'},
}

# write discharge and other output vars to disk for later analysis
OUTPUT_VARNAMES = [
    "Discharge",
]

class Lisflood(AbstractModel):
    """eWaterCycle implementation of Lisflood hydrological model.

    Attributes
        bmi (Bmi): Basic Modeling Interface object
    """

    def setup(self, spinup_start, start, end, dataset):
        """Performs model setup.

        1. Creates config file and config directory
        2. Start bmi container and store as self.bmi

        Args:
            *args: Positional arguments. Sub class should specify each arg.
            **kwargs: Named arguments. Sub class should specify each arg.

        Returns:
            Path to config file and path to config directory
        """
        self.spinup_start = spinup_start
        self.start = start
        self.end = end
        self.dataset = dataset
        config_dir = _create_lisflood_config(self)

        if CFG.container_engine.lower() == 'singularity':
            self.bmi = BmiClientSingularity(
                image=CFG["singularity_images.lisflood"],
                input_dirs=[
                    input_dir,
                    mask_dir,
                    forcing_dir
                    ],
                work_dir=work_dir,
            )
        elif CFG.container_engine.lower() == "docker":
            self.bmi = BmiClientDocker(
                image=CFG["docker_images.lisflood"],
                image_port=55555,
                input_dirs=[
                    input_dir,
                    mask_dir,
                    forcing_dir
                    ],
                work_dir=work_dir,
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG.container_engine}"
            )

        # run_lisvap()

        self.bmi.initialize(config_dir)

    # def run_lisvap(self):
    #     """Run lisvap using singularity image on Cartesius"""
    #     lisvap_file = _create_lisvap_config()
    #     #TODO check if inside directories are needed
    #     !singularity exec -B {self.input_dir}:/data/lisflood_input \
    #         -B {self.mask_dir}:/data/mask -B {self.forcing_dir}:/data/forcing \
    #         -B {self.temp_dir}:/settings -B {self.temp_dir}:/output \
    #         --pwd {self.temp_dir} \
    #         ewatercycle-lisflood-grpc4bmi.sif \
    #         python3 /opt/Lisvap/src/lisvap1.py /settings/{lisvap_file}


    # def get_value_as_xarray(self, name: str) -> xr.DataArray:

    # def run(self, spinup_years, start_years, end_years, variable) -> np.ndarray:

@property
def parameters(self):
    """List the variable names that are available for this model."""
    return self.model.get_output_var_names()


def _create_lisflood_config(self) -> PathLike:
    """Create lisflood config file"""
    cfg = XmlConfig(lisflood_config_path)

    settings = {
        "CalendarDayStart": self.spinup_start.strftime("%d/%m/%Y %H:%M"),
        "StepStart": "1",
        "StepEnd": str((self.end - self.spinup_start).days),
        "PathRoot": f"{input_dir}/Lisflood01degree_masked",
        "MaskMap": f"{mask_dir}/model_mask",
        "PathMeteo": f"{forcing_dir}",
        "PathOut": f"{work_dir}",
    }

    start_year = self.spinup_start.year
    end_year = self.end.year
    timestamp = f"{start_year}_{end_year}"
    dataset = self.dataset

    for textvar in cfg.config.iter("textvar"):
        textvar_name = textvar.attrib["name"]

        # general settings
        for key, value in settings.items():
            if key in textvar_name:
                textvar.set("value", value)

        # input for lisflood
        if "PrefixPrecipitation" in textvar_name:
            textvar.set("value", f"lisflood_{dataset}_pr_{timestamp}")
        if "PrefixTavg" in textvar_name:
            textvar.set("value", f"lisflood_{dataset}_tas_{timestamp}")

        # output of lisvap
        for map_var, prefix in MAPS_PREFIXES.items():
            if prefix['name'] in textvar_name:
                textvar.set(
                    "value",
                    f"lisflood_{dataset}_{prefix['value']}_{timestamp}",
                )
            if map_var in textvar_name:
                textvar.set('value', f"$(PathOut)/$({prefix['name']})")

    # Write to new setting file
    lisflood_file = f"{work_dir}/lisflood_{dataset}_setting.xml"
    cfg.save(lisflood_file)
    return lisflood_file


def _create_lisvap_config(self) -> PathLike:
    """Update lisvap setting file"""
    cfg = XmlConfig(lisflood_config_path)
    # Make a dictionary for settings
    #TODO check if inside directories are needed
    maps = "/data/lisflood_input/Lisflood01degree_masked/maps_netcdf"
    settings = {
        "CalendarDayStart": self.spinup_start.strftime("%d/%m/%Y %H:%M"),
        "StepStart": self.spinup_start.strftime("%d/%m/%Y %H:%M"),
        "StepEnd": self.end.strftime("%d/%m/%Y %H:%M"),
        "PathOut": "/output",
        "PathBaseMapsIn": maps,
        "MaskMap": "/data/mask/model_mask",
        "PathMeteoIn": "/data/forcing",
    }

    start_year = self.spinup_start.year
    end_year = self.end.year
    timestamp = f"{start_year}_{end_year}"

    dataset = self.dataset

    for textvar in cfg.config.iter("textvar"):
        textvar_name = textvar.attrib["name"]

        # general settings
        for key, value in settings.items():
            if key in textvar_name:
                textvar.set("value", value)

        # lisvap input files
        for lisvap_var, cmor_var in INPUT_NAMES.items():
            if lisvap_var in textvar_name:
                filename = f"lisflood_{dataset}_{cmor_var}_{timestamp}"
                textvar.set(
                    "value", f"$(PathMeteoIn)/{filename}",
                )

        # lisvap output files
        for prefix in MAPS_PREFIXES.values():
            if prefix['name'] in textvar_name:
                textvar.set(
                    "value",
                    f"lisflood_{dataset}_{prefix['value']}_{timestamp}",
                )

    # Write to new setting file
    lisvap_file = f"{work_dir}/lisvap_{dataset}_setting.xml"
    cfg.save(lisvap_file)
    return lisvap_file


class XmlConfig(AbstractConfig):
    """Config container where config is read/saved in xml format"""

    def __init__(self, source):
        super().__init__(source)
        self.tree = ET.parse(source)
        self.config = self.tree.getroot()

    def save(self, target):
        self.tree.write(target)


