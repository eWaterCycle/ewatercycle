"""Base classes for eWaterCycle forcings.

Configuring ESMValTool
----------------------

.. _esmvaltool-configuring:

To download data from ESFG via ESMValTool you will need
a ~/.esmvaltool/config-user.yml file with something like:

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
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, TypeAlias, TypeVar

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import fiona
import matplotlib.axes
import matplotlib.pyplot as plt
import shapely
import shapely.geometry
import xarray as xr
from pydantic import BaseModel
from pydantic.functional_validators import AfterValidator, model_validator
from pyproj import Geod
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


def _to_absolute_path(v: str | Path):
    """Absolute path validator."""
    return to_absolute_path(v)


# Needed so subclass.generate() can return type of subclass instead of base class.
AnyForcing = TypeVar("AnyForcing", bound="DefaultForcing")
"""TypeVar for forcing classes."""
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
    shape: Path | None = None
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
                :py:class:`ewatercycle.esmvaltool.schema.Dataset` constructor.
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
            model_specific_options: Subclass specific options.
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
        msg = "No default recipe available."
        raise NotImplementedError(msg)

    @classmethod
    def _run_recipe(
        cls,
        recipe: Recipe,
        directory: Path | None = None,
    ) -> dict[str, str]:
        return run_recipe(recipe, directory)

    def save(self):
        """Export forcing data for later use."""
        yaml = YAML()
        if self.directory is None:
            msg = "Cannot save forcing without directory."
            raise ValueError(msg)
        target = self.directory / FORCING_YAML
        # We want to make the yaml and its parent movable,
        # so the directory should not be included in the yaml file
        clone = self.model_copy()

        # Copy shapefile so statistics like area can be derived
        if clone.shape is not None:
            if not clone.shape.is_relative_to(clone.directory):
                new_shp_path = Path(
                    shutil.copy(clone.shape, clone.directory / clone.shape.name)
                )
                if not clone.shape.with_suffix(".prj").exists():
                    msg = (
                        "Your shape file is missing the .prj projection file.\n"
                        "This file is required, as we cannot guess what projection your"
                        "shapefile is in."
                    )
                    raise FileNotFoundError(msg)
                # Also copy other required files:
                for ext in [".dbf", ".shx", ".prj"]:
                    shutil.copy(
                        clone.shape.with_suffix(ext),
                        clone.directory / clone.shape.with_suffix(ext).name,
                    )
                clone.shape = new_shp_path
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
            msg = (
                f"Forcing file {meta} not found. "
                f"Perhaps you want to use {cls.__name__}(...)?"
            )
            raise FileNotFoundError(msg)
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
        """Return the names of the variables.

        Shorthand for self.filenames.keys()
        """
        return tuple(self.filenames)

    def get_shape_area(self) -> float:
        """Return the area of the shapefile in m2."""
        if self.shape is None:
            msg = "Shapefile not specified"
            raise ValueError(msg)

        shape = fiona.open(self.shape)
        poly = shapely.geometry.shape(next(shape)["geometry"])
        geod = Geod(ellps="WGS84")
        poly_area, _ = geod.geometry_area_perimeter(poly)
        return abs(poly_area)

    def plot_shape(
        self, ax: matplotlib.axes._axes.Axes | None = None
    ) -> matplotlib.axes._axes.Axes:
        """Make a plot of the shapefile on a map of the world.

        The plot is padded with 10% of the north-south extend,
        or the east-west extend (which ever is smallest).

        Optionally a matplotlib axes object can be passed into
        which the shape is plotted.

        The axis object is returned.
        """
        if self.shape is None:
            msg = "Shapefile not specified"
            raise ValueError(msg)

        shape = fiona.open(self.shape)
        poly = shapely.geometry.shape(next(shape)["geometry"])
        w, s, e, n = poly.bounds  # different order than set_extent expects

        # 10 % of the minimum of either the west-east extend or the north-south extend
        #  is used as padding around the shape.
        pad = min(abs(w - e), abs(n - s)) * 0.1

        if ax is None:
            axis_provided = False
            plt.figure(figsize=(8, 5))
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.add_feature(cfeature.COASTLINE, linewidth=1)  # type: ignore[attr-defined]
            ax.add_feature(cfeature.RIVERS, linewidth=1)  # type: ignore[attr-defined]
            ax.add_feature(cfeature.OCEAN, edgecolor="none", facecolor="#4287f5")  # type: ignore[attr-defined]

        else:
            axis_provided = True
            if not hasattr(ax, "add_geometries"):
                msg = (
                    "The provided axis does not have an add_geometries attribute, \n"
                    " thus no spatial projection. This is required to plot a shape.\n"
                    "Create a figure like the following instead:\n"
                    "    plt.figure(figsize=(8, 5))\n"
                    "    ax = plt.axes(projection=ccrs.PlateCarree())\n"
                )
                raise ValueError(msg)

        ax.add_geometries(  # type: ignore[attr-defined]
            poly,
            crs=ccrs.PlateCarree(),
            facecolor="#f5b41d",
            edgecolor="k",
            alpha=0.8,
        )

        if not axis_provided:
            ax.set_extent((w - pad, e + pad, s - pad, n + pad), crs=ccrs.PlateCarree())  # type: ignore[attr-defined]

        return ax

    def __eq__(self, other):
        """Check if two Forcing objects are equal."""
        return self.__dict__ == other.__dict__

    def __getitem__(self, key: str) -> Path:
        """Allows for easy access to the (absolute) path of a forcing variable file."""
        if key in self.filenames:
            return (self.directory / self.filenames[key]).absolute()
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
    """  # noqa: E501

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str | dict,
        variables: tuple[str, ...] = (),
        **model_specific_options,  # noqa: ARG003
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
    """  # noqa: E501

    @classmethod
    def _build_recipe(
        cls,
        start_time: datetime,
        end_time: datetime,
        shape: Path,
        dataset: Dataset | str | dict,
        variables: tuple[str, ...] = (),
        **model_specific_options,  # noqa: ARG003
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


class GenericDistributedForcing(_GenericForcing, DistributedUserForcing):
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


class GenericLumpedForcing(_GenericForcing, LumpedUserForcing):
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
