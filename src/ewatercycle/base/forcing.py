"""Base classes for eWaterCycle forcings.

Configuring ESMValTool
----------------------

.. _esmvaltool-configuring:

To download data from ESFG via ESMValTool you will need a ~/.esmvaltool/config-user.yml file with something like:

.. code-block:: yaml

    search_esgf: when_missing
    download_dir: ~/climate_data
    rootpath:
        CMIP6: ~/climate_data/CMIP6
    drs:
        CMIP6: ESGF

A config file can be generated with:

.. code-block:: bash

    esmvaltool config get-config-user

See `ESMValTool configuring docs <https://docs.esmvaltool.org/projects/ESMValCore/en/latest/quickstart/configure.html#user-configuration-file>`_
for more information.
"""
import logging
import shutil
import warnings
from datetime import datetime
from pathlib import Path
from typing import Annotated, Callable, Optional, TypeAlias, TypeVar, Union

import xarray as xr
from pydantic import BaseModel
from pydantic.functional_validators import AfterValidator, model_validator
from ruamel.yaml import YAML

from ewatercycle.esmvaltool.builder import (
    build_generic_distributed_forcing_recipe,
    build_generic_lumped_forcing_recipe,
)
from ewatercycle.esmvaltool.run import run_recipe
from ewatercycle.esmvaltool.schema import Dataset, Recipe
from ewatercycle.util import get_time, merge_esvmaltool_datasets, to_absolute_path

logger = logging.getLogger(__name__)
FORCING_YAML = "ewatercycle_forcing.yaml"


def _to_absolute_path(v: Union[str, Path]):
    """Absolute path validator."""
    return to_absolute_path(v)


# Needed so subclass.generate() can return type of subclass instead of base class.
AnyForcing = TypeVar("AnyForcing", bound="DefaultForcing")
Postprocessor: TypeAlias = Callable[[dict[str, str]], tuple[str, ...]]


class DefaultForcing(BaseModel):
    """Container for forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
            If relative then it is relative to the given directory.
        filenames: Dictionary of the variables contained in this forcing object, as well
            as the file names. Default value is empty, for backwards compatibility.
    """

    # TODO add validation for start_time and end_time
    # using https://docs.pydantic.dev/latest/usage/types/datetime/
    # TODO make sure start_time < end_time
    start_time: str
    end_time: str
    directory: Annotated[Path, AfterValidator(_to_absolute_path)]
    shape: Optional[Path] = None
    filenames: dict[str, str] = {}  # Default value for backwards compatibility

    @model_validator(mode="after")
    def _absolute_shape(self):
        if self.shape is not None:
            self.shape = to_absolute_path(
                self.shape, parent=self.directory, must_be_in_parent=False
            )
        if self.filenames == {}:
            warnings.warn(
                message=(
                    "Forcing stores the filenames in the 'filenames' dict since "
                    "ewatercycle version 2.1, instead of as separate properties.\n"
                    "In a future version this argument will become required instead of "
                    "optional."
                ),
                category=DeprecationWarning,
                stacklevel=1,
            )
        return self

    @classmethod
    def generate(
        cls: type[AnyForcing],
        dataset: str | Dataset | dict,
        start_time: str,
        end_time: str,
        shape: str | Path,
        directory: str | None = None,
        variables: tuple[str, ...] = (),
        postprocessor: Postprocessor | None = None,
        **model_specific_options,
    ) -> AnyForcing:
        """Generate forcings for a model.

        The forcing is generated with help of
        `ESMValTool <https://esmvaltool.org/>`_.

        Args:
            dataset: Dataset to get forcing data from.
                When string is given a predefined dataset is looked up in
                :py:const:`ewatercycle.esmvaltool.datasets.DATASETS`.
                When dict given it is passed to
                :py:class:`ewatercycle.esmvaltool.models.Dataset` constructor.
            start_time: Start time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            end_time: nd time of forcing in UTC and ISO format string e.g.
                'YYYY-MM-DDTHH:MM:SSZ'.
            shape: Path to a shape file. Used for spatial selection.
            directory: Directory in which forcing should be written.
                If not given will create timestamped directory.
            variables: Variables which need to be downloaded/preprocessed by ESMValTool.
            postprocessor: A custom post-processor that can, e.g., derive additional
                variables based on the ESMValTool recipe output. Must return
                the names & filenames of the variables it derived.
        """
        recipe = cls._build_recipe(
            dataset=dataset,
            start_time=get_time(start_time),
            end_time=get_time(end_time),
            shape=Path(shape),
            variables=variables,
            **model_specific_options,
        )

        recipe_output = cls._run_recipe(
            recipe, directory=Path(directory) if directory else None
        )

        derived_variables: tuple[str, ...] = ()
        if postprocessor is not None:
            derived_variables = postprocessor(
                recipe_output
            )  # Run possible postprocessor (e.g. derive var)

        directory = recipe_output.pop("directory")
        arguments = cls._recipe_output_to_forcing_arguments(
            recipe_output, model_specific_options
        )
        forcing = cls(
            directory=Path(directory),
            start_time=start_time,
            end_time=end_time,
            shape=Path(shape),
            filenames={
                var: recipe_output[var] for var in variables + derived_variables
            },
            **arguments,
        )
        forcing.save()
        return forcing

    @classmethod
    def _recipe_output_to_forcing_arguments(cls, recipe_output, model_specific_options):
        return {
            **recipe_output,
            **model_specific_options,
        }

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str | dict,
        variables: tuple[str, ...] = (),
        **model_specific_options,
    ) -> Recipe:
        # TODO do we want an implementation here?
        # If so how is it different from GenericDistributedForcing?
        raise NotImplementedError("No default recipe available.")

    @classmethod
    def _run_recipe(
        cls,
        recipe: Recipe,
        directory: Optional[Path] = None,
    ) -> dict[str, str]:
        return run_recipe(recipe, directory)

    def save(self):
        """Export forcing data for later use."""
        yaml = YAML()
        if self.directory is None:
            raise ValueError("Cannot save forcing without directory.")
        target = self.directory / FORCING_YAML
        # We want to make the yaml and its parent movable,
        # so the directory should not be included in the yaml file
        clone = self.model_copy()

        # Copy shapefile so statistics like area can be derived
        if clone.shape is not None:
            if not clone.shape.is_relative_to(clone.directory):
                clone.shape = Path(
                    shutil.copy(clone.shape, clone.directory / clone.shape.name)
                )
            clone.shape = clone.shape.relative_to(clone.directory)

        fdict = clone.model_dump(exclude={"directory"}, exclude_none=True, mode="json")
        with target.open("w") as f:
            yaml.dump(fdict, f)
        return target

    @classmethod
    def load(cls, directory: str | Path):
        """Load previously generated or imported forcing data.

        Args:
            directory: forcing data directory; must contain
                `ewatercycle_forcing.yaml` file

        Returns: Forcing object
        """
        data_source = to_absolute_path(directory)
        meta = data_source / FORCING_YAML
        yaml = YAML(typ="safe")

        if not meta.exists():
            raise FileNotFoundError(
                f"Forcing file {meta} not found. "
                f"Perhaps you want to use {cls.__name__}(...)?"
            )
        metadata = meta.read_text()
        # Workaround for legacy forcing files having !PythonClass tag.
        # Remove it so ewatercycle.forcing.source[<forcing name>].load(dir) works.
        metadata = metadata.replace(f"!{cls.__name__}", "")

        fdict = yaml.load(metadata)
        fdict["directory"] = data_source

        return cls(**fdict)

    def to_xarray(self) -> xr.Dataset:
        """Return this Forcing object as an xarray Dataset."""
        if len(self.filenames) == 0:
            msg = "There are no variables stored in this Forcing object."
            raise ValueError(msg)
        if not all(fname.endswith(".nc") for _, fname in self.filenames.items()):
            msg = (
                "Not all files are netCDF files. Only netCDF files can be opened as "
                "an xarray Dataset."
            )
            raise ValueError(msg)
        fpaths = [self.directory / filename for _, filename in self.filenames.items()]

        datasets = [xr.open_dataset(fpath, chunks="auto") for fpath in fpaths]
        return merge_esvmaltool_datasets(datasets)

    def variables(self) -> tuple[str, ...]:
        """Return the names of the variables. Shorthand for self.filenames.keys()"""
        return tuple([key for key in self.filenames])

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __getitem__(self, key: str) -> Path:
        """Allows for easy access to the (absolute) path of a forcing variable file."""
        if key in self.filenames:
            return (self.directory / self.filenames[key]).absolute()
        else:
            msg = f"'{key}' is not a valid variable for this forcing object."
            raise KeyError(msg)


class DistributedUserForcing(DefaultForcing):
    """Forcing object with user-specified downloaded variables and postprocessing.

    Examples:

    To generate forcing from ERA5 for the Rhine catchment for 2000-2001, retrieving
    the 'pr', 'tas' and 'rsds' variables, and applying the Makkink evaporation
    postprocessor.

    .. code-block:: python

        from pathlib import Path
        from rich import print
        from ewatercycle.base.forcing import DistributedUserForcing

        cmip_dataset = {
            "dataset": "EC-Earth3",
            "project": "CMIP6",
            "grid": "gr",
            "exp": "historical",
            "ensemble": "r6i1p1f1",
        }
        shape = Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp")
        forcing = DistributedUserForcing.generate(
            dataset=cmip_dataset,
            start_time='2000-01-01T00:00:00Z',
            end_time='2001-01-01T00:00:00Z',
            shape=str(shape.absolute()),
            variables=("pr", "tas"),
        )
        print(forcing)

    Gives something like:

    .. code-block:: python

        DistributedUserForcing(
            start_time='2000-01-01T00:00:00Z',
            end_time='2001-01-01T00:00:00Z',
            directory=PosixPath('/home/bart/esmvaltool_output/ewcrepvl1jeunb_20240305_131155/work/diagnostic/script'),
            shape=PosixPath('/home/bart/git/ewatercycle/src/ewatercycle/testing/data/Rhine/Rhine.shp'),
            filenames={
                'pr': 'CMIP6_EC-Earth3_day_historical_r6i1p1f1_pr_gr_2000-2001.nc',
                'tas': 'CMIP6_EC-Earth3_day_historical_r6i1p1f1_tas_gr_2000-2001.nc',
                'rsds': 'CMIP6_EC-Earth3_day_historical_r6i1p1f1_rsds_gr_2000-2001.nc',
                'evspsblpot': 'Derived_Makkink_evspsblpot.nc'
            }
        )
    """

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str | dict,
        variables: tuple[str, ...] = (),
        **model_specific_options,
    ):
        return build_generic_distributed_forcing_recipe(
            # TODO allow finer selection then a whole year.
            # using ISO 8601 str as type or timerange attribute see
            # https://docs.esmvaltool.org/projects/ESMValCore/en/latest/recipe/overview.html#recipe-section-datasets
            start_year=start_time.year,
            end_year=end_time.year,
            shape=shape,
            dataset=dataset,
            variables=variables,
        )


class LumpedUserForcing(DistributedUserForcing):
    """Forcing object with user-specified downloaded variables and postprocessing.

    Examples:

    To generate lumped forcing from ERA5 for the Rhine catchment for 2000-2001,
    retrieving the 'pr', 'tas' and 'rsds' variables, and applying the Makkink
    evaporation postprocessor.

    .. code-block:: python

        from pathlib import Path
        from rich import print
        from ewatercycle.base.forcing import LumpedUserForcing

        cmip_dataset = {
            "dataset": "EC-Earth3",
            "project": "CMIP6",
            "grid": "gr",
            "exp": "historical",
            "ensemble": "r6i1p1f1",
        }
        shape = Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp")
        forcing = LumpedUserForcing.generate(
            dataset=cmip_dataset,
            start_time='2000-01-01T00:00:00Z',
            end_time='2001-01-01T00:00:00Z',
            shape=str(shape.absolute()),
            variables=("pr", "tas"),
        )
        print(forcing)

    Gives something like:

    .. code-block:: python

        LumpedUserForcing(
            start_time='2000-01-01T00:00:00Z',
            end_time='2001-01-01T00:00:00Z',
            directory=PosixPath('/home/bart/esmvaltool_output/ewcrepvl1jeunb_20240305_131155/work/diagnostic/script'),
            shape=PosixPath('/home/bart/git/ewatercycle/src/ewatercycle/testing/data/Rhine/Rhine.shp'),
            filenames={
                'pr': 'CMIP6_EC-Earth3_day_historical_r6i1p1f1_pr_gr_2000-2001.nc',
                'tas': 'CMIP6_EC-Earth3_day_historical_r6i1p1f1_tas_gr_2000-2001.nc',
                'rsds': 'CMIP6_EC-Earth3_day_historical_r6i1p1f1_rsds_gr_2000-2001.nc',
                'evspsblpot': 'Derived_Makkink_evspsblpot.nc'
            }
        )
    """

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str | dict,
        variables: tuple[str, ...] = (),
        **model_specific_options,
    ):
        return build_generic_lumped_forcing_recipe(
            # TODO allow finer selection then a whole year.
            # using ISO 8601 str as type or timerange attribute see
            # https://docs.esmvaltool.org/projects/ESMValCore/en/latest/recipe/overview.html#recipe-section-datasets
            start_year=start_time.year,
            end_year=end_time.year,
            shape=shape,
            dataset=dataset,
            variables=variables,
        )


class _GenericForcing(DefaultForcing):
    @classmethod
    def generate(  # type: ignore[override]
        cls: type[AnyForcing],
        dataset: str | Dataset | dict,
        start_time: str,
        end_time: str,
        shape: str | Path,
        directory: str | None = None,
        **model_specific_options,
    ) -> AnyForcing:
        return super().generate(
            dataset,
            start_time,
            end_time,
            shape,
            directory,
            variables=("pr", "tas"),
            postprocessor=None,
            **model_specific_options,
        )


class GenericDistributedForcing(_GenericForcing, DistributedUserForcing):  # type: ignore[misc]
    """Generic forcing data for a distributed model.

    Examples:

        To generate forcing from ERA5 for the Rhine catchment for 2000-2001:

        .. code-block:: python

            from pathlib import Path
            from rich import print
            from ewatercycle.base.forcing import GenericDistributedForcing

            shape = Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp")
            forcing = GenericDistributedForcing.generate(
                dataset='ERA5',
                start_time='2000-01-01T00:00:00Z',
                end_time='2001-01-01T00:00:00Z',
                shape=shape.absolute(),
            )
            print(forcing)

        Gives something like:

        .. code-block:: python

            GenericDistributedForcing(
                model='generic_distributed',
                start_time='2000-01-01T00:00:00Z',
                end_time='2001-01-01T00:00:00Z',
                directory=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/esmvaltool_output/tmp05upitxoewcrep_20230815_154640/work/diagnostic/script'),
                shape=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/src/ewatercycle/testing/data/Rhine/Rhine.shp'),
                filenames={
                    pr='OBS6_ERA5_reanaly_1_day_pr_2000-2001.nc',
                    tas='OBS6_ERA5_reanaly_1_day_tas_2000-2001.nc',
                }
            )

        To generate forcing from CMIP6 for the Rhine catchment for 2000-2001
        (make sure :ref:`ESMValTool is configured <esmvaltool-configuring>` correctly):

        .. code-block:: python

            from pathlib import Path
            from rich import print
            from ewatercycle.base.forcing import GenericDistributedForcing

            shape = Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp")
            cmip_dataset = {
                "dataset": "EC-Earth3",
                "project": "CMIP6",
                "grid": "gr",
                "exp": ["historical",],
                "ensemble": "r6i1p1f1",
            }

            forcing = GenericDistributedForcing.generate(
                dataset=cmip_dataset,
                start_time="2000-01-01T00:00:00Z",
                end_time="2001-01-01T00:00:00Z",
                shape=shape.absolute(),
            )
            print(forcing)

        Gives something like:

        .. code-block:: python

            GenericDistributedForcing(
                start_time='2000-01-01T00:00:00Z',
                end_time='2001-01-01T00:00:00Z',
                directory=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/esmvaltool_output/ewcrep0ibzlds__20230904_082748/work/diagnostic/script'),
                shape=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/src/ewatercycle/testing/data/Rhine/Rhine.shp'),
                filenames={
                    pr='CMIP6_EC-Earth3_day_historical_r6i1p1f1_pr_gr_2000-2001.nc',
                    tas='CMIP6_EC-Earth3_day_historical_r6i1p1f1_tas_gr_2000-2001.nc',
                }
            )
    """

    ...


class GenericLumpedForcing(_GenericForcing, LumpedUserForcing):  # type: ignore[misc]
    """Generic forcing data for a lumped model.

    Example:

        To generate forcing from ERA5 for the Rhine catchment for 2000-2001:

        .. code-block:: python

            from pathlib import Path
            from rich import print
            from ewatercycle.base.forcing import GenericLumpedForcing

            shape = Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp")
            forcing = GenericLumpedForcing.generate(
                dataset='ERA5',
                start_time='2000-01-01T00:00:00Z',
                end_time='2001-01-01T00:00:00Z',
                shape=shape.absolute(),
            )
            print(forcing)

        Gives something like:

        .. code-block:: python

            GenericLumpedForcing(
                model='generic_distributed',
                start_time='2000-01-01T00:00:00Z',
                end_time='2001-01-01T00:00:00Z',
                directory=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/esmvaltool_output/ewcrep90hmnvat_20230816_124951/work/diagnostic/script'),
                shape=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/src/ewatercycle/testing/data/Rhine/Rhine.shp'),
                pr='OBS6_ERA5_reanaly_1_day_pr_2000-2001.nc',
                tas='OBS6_ERA5_reanaly_1_day_tas_2000-2001.nc',
                tasmin='OBS6_ERA5_reanaly_1_day_tasmin_2000-2001.nc',
                tasmax='OBS6_ERA5_reanaly_1_day_tasmax_2000-2001.nc'
            )

        To generate forcing from CMIP6 for the Rhine catchment for 2000-2001
        (make sure :ref:`ESMValTool is configured <esmvaltool-configuring>` correctly):

        .. code-block:: python

            from pathlib import Path
            from rich import print
            from ewatercycle.base.forcing import GenericLumpedForcing

            shape = Path("./src/ewatercycle/testing/data/Rhine/Rhine.shp")
            cmip_dataset = {
                "dataset": "EC-Earth3",
                "project": "CMIP6",
                "grid": "gr",
                "exp": ["historical",],
                "ensemble": "r6i1p1f1",
            }

            forcing = GenericLumpedForcing.generate(
                dataset=cmip_dataset,
                start_time="2000-01-01T00:00:00Z",
                end_time="2001-01-01T00:00:00Z",
                shape=shape.absolute(),
            )
            print(forcing)
    """

    # files returned by generate() have only time coordinate and zero lons/lats.
    # TODO inject centroid of shape as single lon/lat into files?
    # use diagnostic script or overwrite generate()
    ...
