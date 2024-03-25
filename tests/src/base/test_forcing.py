from pathlib import Path
from shutil import copytree
from unittest import mock

import pytest
import xarray as xr

from ewatercycle._forcings.makkink import (
    DistributedMakkinkForcing,
    LumpedMakkinkForcing,
    derive_e_pot,
)
from ewatercycle.base.forcing import (
    FORCING_YAML,
    DistributedUserForcing,
    GenericDistributedForcing,
    LumpedUserForcing,
)

# Use GenericDistributedForcing to test abstract DefaultForcing class


class TestGenericDistributedForcingWithExternalShape:
    """External shape files are now copied into the forcing directory."""

    def test_save(self, tmp_path: Path, sample_shape: str):
        forcing = GenericDistributedForcing(
            directory=tmp_path,
            shape=Path(sample_shape),
            start_time="2000-01-01T00:00:00Z",
            end_time="2001-01-01T00:00:00Z",
            filenames={
                "pr": "OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc",
                "tas": "OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc",
                "tasmin": "OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc",
                "tasmax": "OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc",
            },
        )
        forcing.save()

        fn = tmp_path / FORCING_YAML
        content = fn.read_text()

        expected = """\
start_time: '2000-01-01T00:00:00Z'
end_time: '2001-01-01T00:00:00Z'
shape: Rhine.shp
filenames:
  pr: OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc
  tas: OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc
  tasmin: OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc
  tasmax: OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc
"""

        assert content == expected


class TestGenericDistributedForcingWithInternalShape:
    def test_save(self, tmp_path: Path, sample_shape: str):
        # Copy shape to tmp_path
        shape_dir = Path(sample_shape).parent
        copytree(shape_dir, tmp_path / shape_dir.name)
        shape = tmp_path / shape_dir.name / Path(sample_shape).name

        forcing = GenericDistributedForcing(
            directory=tmp_path,
            shape=shape,
            start_time="2000-01-01T00:00:00Z",
            end_time="2001-01-01T00:00:00Z",
            filenames={
                "pr": "OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc",
                "tas": "OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc",
                "tasmin": "OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc",
                "tasmax": "OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc",
            },
        )
        forcing.save()

        fn = tmp_path / FORCING_YAML
        content = fn.read_text()

        expected = """\
start_time: '2000-01-01T00:00:00Z'
end_time: '2001-01-01T00:00:00Z'
shape: Rhine/Rhine.shp
filenames:
  pr: OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc
  tas: OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc
  tasmin: OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc
  tasmax: OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc
"""

        assert content == expected


class TestGenericDistributedForcingWithoutShape:
    def test_save(self, tmp_path: Path):
        forcing = GenericDistributedForcing(
            directory=tmp_path,
            start_time="2000-01-01T00:00:00Z",
            end_time="2001-01-01T00:00:00Z",
            filenames={
                "pr": "OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc",
                "tas": "OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc",
                "tasmin": "OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc",
                "tasmax": "OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc",
            },
        )
        forcing.save()

        fn = tmp_path / FORCING_YAML
        content = fn.read_text()

        expected = """\
start_time: '2000-01-01T00:00:00Z'
end_time: '2001-01-01T00:00:00Z'
filenames:
  pr: OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc
  tas: OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc
  tasmin: OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc
  tasmax: OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc
"""

        assert content == expected

    def test_load(self, tmp_path: Path):
        fn = tmp_path / FORCING_YAML
        fn.write_text(
            """\
start_time: '2000-01-01T00:00:00Z'
end_time: '2001-01-01T00:00:00Z'
filenames:
  pr: OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc
  tas: OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc
  tasmin: OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc
  tasmax: OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc
"""
        )

        forcing = GenericDistributedForcing.load(tmp_path)

        expected = GenericDistributedForcing(
            directory=tmp_path,
            start_time="2000-01-01T00:00:00Z",
            end_time="2001-01-01T00:00:00Z",
            filenames={
                "pr": "OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc",
                "tas": "OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc",
                "tasmin": "OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc",
                "tasmax": "OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc",
            },
        )
        assert forcing == expected

    def test_load_legacy(self, tmp_path: Path):
        fn = tmp_path / FORCING_YAML
        fn.write_text(
            """\
!GenericDistributedForcing
start_time: '2000-01-01T00:00:00Z'
end_time: '2001-01-01T00:00:00Z'
pr: OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc
tas: OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc
tasmin: OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc
tasmax: OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc
        """
        )

        forcing = GenericDistributedForcing.load(tmp_path)

        expected = GenericDistributedForcing(
            directory=tmp_path,
            start_time="2000-01-01T00:00:00Z",
            end_time="2001-01-01T00:00:00Z",
            pr="OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc",
            tas="OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc",
            tasmin="OBS6_ERA5_reanaly_*_day_tasmin_2000-2001.nc",
            tasmax="OBS6_ERA5_reanaly_*_day_tasmax_2000-2001.nc",
        )
        assert forcing == expected


class TestMakkinkUserForcing:
    @pytest.mark.parametrize(
        "forcing_class",
        [
            DistributedMakkinkForcing,
            LumpedMakkinkForcing,
            DistributedUserForcing,
            LumpedUserForcing,
        ],
    )
    def test_save_distributed(self, forcing_class, tmp_path: Path, sample_shape: str):
        # Copy shape to tmp_path
        shape_dir = Path(sample_shape).parent
        copytree(shape_dir, tmp_path / shape_dir.name)
        shape = tmp_path / shape_dir.name / Path(sample_shape).name

        forcing = forcing_class(
            directory=tmp_path,
            shape=shape,
            start_time="2000-01-01T00:00:00Z",
            end_time="2001-01-01T00:00:00Z",
            filenames={
                "pr": "OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc",
                "tas": "OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc",
                "rsds": "OBS6_ERA5_reanaly_*_day_rsds_2000-2001.nc",
                "evspsblpot": "Derived_Makkink_evspsblpot.nc",
            },
        )
        forcing.save()

        fn = tmp_path / FORCING_YAML
        content = fn.read_text()

        expected = """\
start_time: '2000-01-01T00:00:00Z'
end_time: '2001-01-01T00:00:00Z'
shape: Rhine/Rhine.shp
filenames:
  pr: OBS6_ERA5_reanaly_*_day_pr_2000-2001.nc
  tas: OBS6_ERA5_reanaly_*_day_tas_2000-2001.nc
  rsds: OBS6_ERA5_reanaly_*_day_rsds_2000-2001.nc
  evspsblpot: Derived_Makkink_evspsblpot.nc
"""

        assert content == expected


@pytest.fixture
def recipe_output(tmp_path: Path) -> dict:
    forcing_dir = Path(__file__).parent.parent / "esmvaltool/files"
    output_dir = tmp_path / "output"
    copytree(forcing_dir, output_dir)

    return {
        "directory": output_dir,
        "tas": "OBS6_ERA5_reanaly_1_day_tas_2000-2000.nc",
        "rsds": "OBS6_ERA5_reanaly_1_day_rsds_2000-2000.nc",
        "pr": "OBS6_ERA5_reanaly_1_day_pr_2000-2000.nc",
    }


def test_makkink_derivation(recipe_output):
    derive_e_pot(recipe_output)

    assert "evspsblpot" in recipe_output

    ds = xr.open_dataset(recipe_output["directory"] / recipe_output["evspsblpot"])  # type: ignore
    assert not ds["evspsblpot"].mean(dim=["lat", "lon"]).isnull().any("time")


def test_integration_makkink_forcing(sample_shape, recipe_output):
    def recipe_output_cls(cls, *args, **kwargs):
        return recipe_output

    with mock.patch.object(
        DistributedMakkinkForcing, "_run_recipe", new=recipe_output_cls
    ):
        forcing = DistributedMakkinkForcing.generate(
            dataset="ERA5",
            start_time="2000-01-01T00:00:00Z",
            end_time="2000-12-31T00:00:00Z",
            shape=sample_shape,
        )

        assert (
            not forcing.to_xarray()["evspsblpot"]
            .mean(dim=["lat", "lon"])
            .isnull()
            .any("time")
        )
