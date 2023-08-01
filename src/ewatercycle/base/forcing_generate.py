from pathlib import Path

from pydantic import BaseModel
from ruamel.yaml import YAML

from ewatercycle.base.esmvaltool_wrapper import Dataset, Recipe
from ewatercycle.base.forcing import DATASETS, DefaultForcing

# TODO move here
from ewatercycle.util import data_files_from_recipe_output


class eWaterCycleRecipe(Recipe):
    """wrapper around ESMValTool Recipe with some useful additions for hydrology recipes."""

    @classmethod
    def load(cls, path):
        yaml = YAML(typ="safe")
        raw_recipe = yaml.load(path)
        return cls(**raw_recipe)

    def update_dataset(self, dataset):
        if isinstance(dataset, str):
            dataset = Dataset(**DATASETS[dataset])
            self.datasets = [dataset]

    def update_startendtime(self, start_time, end_time):
        assert self.diagnostics is not None, "Invalid recipe"
        variables = self.diagnostics["diagnostic"].variables
        assert variables is not None, "Invalid recipe"
        for variable in variables.values():
            variable.start_year = start_time.year
            variable.end_year = end_time.year

    def update_shape(self, shape):
        assert self.preprocessors is not None, "Invalid recipe"
        for preprocessor in self.preprocessors.values():
            if "extract_shape" in preprocessor:
                preprocessor["extract_shape"]["shapefile"] = str(shape)

    # def update_timerange(self, timerange):
    # pass

    def run(self):
        pass


class GenericDistributedForcing(DefaultForcing):

    variables: dict[str, Path]

    @classmethod
    def generate(cls, dataset, start_time, end_time, timerange, shape, **_model_kwargs):
        template = Path(__file__).parent / "recipe_gendist.yaml"
        recipe = eWaterCycleRecipe.load(template)
        recipe.update_dataset(dataset)
        recipe.update_startendtime(start_time, end_time)
        # recipe.update_timerange()
        recipe.update_shape(shape)

        # Optional: here subclasses can add custom modifications

        recipe_output = recipe.run()

        forcing_args = {"start_time": start_time, "end_time": end_time, "shape": shape}
        forcing_args.update(parse_recipe_output(recipe_output))
        return cls(**forcing_args)


def parse_recipe_output(recipe_output):
    directory, variables = data_files_from_recipe_output(recipe_output)
    # Mold ESMValTool output into the format needed for GenericDistributedForcing
    return {"directory": directory, "variables": variables}


class PCRGlobWBForcing(DefaultForcing):

    # TODO add target model

    @classmethod
    def generate(
        cls,
        dataset,
        start_time,
        end_time,
        timerange,
        shape,
        start_time_climatology,
        end_time_climatology,
    ):
        """Custom docstring."""
        template = Path(__file__).parent / "recipe_gendist.yaml"
        recipe = eWaterCycleRecipe.load(template)
        recipe.update_dataset(dataset)
        recipe.update_startendtime(start_time, end_time)
        recipe.update_shape(shape)

        # Here the subclasses can implement custom modifications
        update_recipe_pcrglobwb(
            recipe,
            arg1,
            arg2,
        )

        recipe_output = recipe.run()

        forcing_args = {"start_time": start_time, "end_time": end_time, "shape": shape}
        forcing_args.update(parse_recipe_output_pcrglobwb(recipe_output))
        return cls(**forcing_args)


def update_recipe_pcrglobwb(
    recipe,
    arg1,
    arg2,
):
    # custom updates needed for specific model
    pass


def parse_recipe_output_pcrglobwb(recipe_output):
    # Mold ESMValTool output into the format needed for PCRGlobWB Forcing
    directory, variables = data_files_from_recipe_output(recipe_output)
    return {
        "directory": directory,
        "precipitationNC": variables["pr"],
        "temperatureNC": variables["tas"],
    }
