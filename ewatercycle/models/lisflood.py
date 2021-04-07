
from ewatercycle.models.abstract import AbstractModel
from grpc4bmi.bmi_client_singularity import BmiClientSingularity
from grpc4bmi.bmi_client_docker import BmiClientDocker
from ewatercycle import CFG



class Lisflood(AbstractModel):
    """eWaterCycle implementation of Lisflood hydrological model.

    Attributes
        bmi (Bmi): Basic Modeling Interface object
    """

    def setup(self, forcing_dir, work_dir):
        """Performs model setup.

        1. Creates config file and config directory
        2. Start bmi container and store as self.bmi

        Args:
            *args: Positional arguments. Sub class should specify each arg.
            **kwargs: Named arguments. Sub class should specify each arg.

        Returns:
            Path to config file and path to config directory
        """
        config_dir = self._create_config()

        if CFG.container_engine.lower() == 'singularity':
            container_image = 'ewatercycle-lisflood-grpc4bmi.sif'
            self.bmi = BmiClientSingularity(
                image=container_image,
                input_dirs=[
                    CFG.lisflood.input_dir,
                    CFG.lisflood.mask_dir,
                    forcing_dir
                    ],
                work_dir=work_dir,
            )
        elif CFG.container_engine.lower() == "docker":
            container_image = 'ewatercycle/lisflood-grpc4bmi:latest'
            self.bmi = BmiClientDocker(
                image=container_image,
                image_port=55555,
                input_dirs=[
                    CFG.lisflood.input_dir,
                    CFG.lisflood.mask_dir,
                    forcing_dir
                    ],
                work_dir=work_dir,
            )
        else:
            raise ValueError(
                f"Unknown container technology in CFG: {CFG.container_engine}"
            )

        self.bmi.initialize(config_dir)

    def _create_lisflood_config(self) -> PathLike:

        """Update lisflood setting file"""
        # Make a dictionary for settings
        settings = {
            "CalendarDayStart": self.spinup_start.strftime("%d/%m/%Y %H:%M"),
            "StepStart": "1",
            "StepEnd": str((self.end - self.spinup_start).days),
            "PathRoot": f"{self.input_dir}/Lisflood01degree_masked",
            "MaskMap": f"{self.mask_dir}/model_mask",
            "PathMeteo": f"{self.forcing_dir}",
            "PathOut": f"{self.temp_dir}",
        }

        # Open default setting file
        lisflood_file = (
            self.input_dir / "settings_templates" / "settings_lisflood.xml"
        )
        tree = ET.parse(str(lisflood_file))
        root = tree.getroot()

        start_year = self.spinup_start.year
        end_year = self.end.year
        timestamp = f"{start_year}_{end_year}"

        dataset = self.dataset

        for textvar in root.iter("textvar"):
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
            for map_var, prefix in self.maps_prefixes.items():
                if prefix['name'] in textvar_name:
                    textvar.set(
                        "value",
                        f"lisflood_{dataset}_{prefix['value']}_{timestamp}",
                    )
                if map_var in textvar_name:
                    textvar.set('value', f"$(PathOut)/$({prefix['name']})")

        # Write to new setting file
        lisflood_file = f"lisflood_{self.dataset}_setting.xml"
        tree.write(f"{self.temp_dir}/{lisflood_file}")
        print(f"The lisflood setting file is in "
              f"{self.temp_dir}/{lisflood_file}")
        return f"{self.temp_dir}/{lisflood_file}"



    def get_value_as_xarray(self, name: str) -> xr.DataArray:

    def run(self, spinup_years, start_years, end_years, variable) -> np.ndarray:
        self.model = self.initialize( self.config_file)

@property
def parameters(self):
    """List the variable names that are available for this model."""
    return self.model.get_output_var_names()

