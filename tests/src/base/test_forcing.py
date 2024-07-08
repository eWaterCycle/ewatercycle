import unittest
from pathlib import Path
from shutil import copytree
from unittest import mock

import pytest
import xarray as xr
from cartopy.io import shapereader

from ewatercycle._forcings.caravan import (
    CaravanForcing,
    crop_ds,
    extract_basin_shapefile,
    get_shapefiles,
)
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


@pytest.fixture
def mock_retrieve():
    with mock.patch(
        "ewatercycle._forcings.caravan.CaravanForcing.get_dataset"
    ) as mock_class:
        test_file = Path(__file__).parent / "forcing_files" / "test_caravan_file.nc"
        mock_class.return_value = xr.open_dataset(test_file)
        yield mock_class


def test_retrieve_caravan_forcing(tmp_path: Path, mock_retrieve: mock.MagicMock):
    vars = (
        "timezone",
        "name",
        "country",
        "lat",
        "lon",
        "area",
        "p_mean",
        "pet_mean",
        "aridity",
        "frac_snow",
        "moisture_index",
        "seasonality",
        "high_prec_freq",
        "high_prec_dur",
        "low_prec_freq",
        "low_prec_dur",
        "total_precipitation_sum",
        "potential_evaporation_sum",
        "temperature_2m_mean",
        "temperature_2m_min",
        "temperature_2m_max",
        "streamflow",
    )
    basin_id = "camels_03439000"
    test_files_dir = Path(__file__).parent / "forcing_files"
    tmp_camels_dir = tmp_path / "camels"
    copytree(test_files_dir, tmp_camels_dir)
    caravan_forcing = CaravanForcing.generate(
        start_time="1981-01-01T00:00:00Z",
        end_time="1981-03-01T00:00:00Z",
        directory=str(tmp_camels_dir),
        basin_id=basin_id,
        variables=vars,
    )
    caravan_forcing.save()
    ds = caravan_forcing.to_xarray()
    content = list(ds.data_vars.keys())
    expected = ["Q", "evspsblpot", "pr", "tas", "tasmax", "tasmin"]
    assert content == expected
    mock_retrieve.assert_called_once_with(basin_id.split("_")[0])

    assert caravan_forcing.to_xarray()["evspsblpot"].attrs["unit"] == "kg m-2 s-1"
    assert caravan_forcing.to_xarray()["pr"].attrs["unit"] == "kg m-2 s-1"
    assert caravan_forcing.to_xarray()["tas"].attrs["unit"] == "K"


def test_retrieve_caravan_forcing_empty_vars(
    tmp_path: Path, mock_retrieve: mock.MagicMock
):
    basin_id = "camels_03439000"
    test_files_dir = Path(__file__).parent / "forcing_files"
    tmp_camels_dir = tmp_path / "camels"
    copytree(test_files_dir, tmp_camels_dir)
    caravan_forcing = CaravanForcing.generate(
        start_time="1981-01-01T00:00:00Z",
        end_time="1981-03-01T00:00:00Z",
        directory=str(tmp_camels_dir),
        basin_id=basin_id,
    )
    caravan_forcing.save()
    ds = caravan_forcing.to_xarray()
    content = list(ds.data_vars.keys())
    expected = ["Q", "evspsblpot", "pr", "tas", "tasmax", "tasmin"]
    assert content == expected
    mock_retrieve.assert_called_once_with(basin_id.split("_")[0])


def test_retrieve_caravan_forcing_no_basin_id(
    tmp_path: Path, mock_retrieve: mock.MagicMock
):
    test_files_dir = Path(__file__).parent / "forcing_files"
    tmp_camels_dir = tmp_path / "camels"
    copytree(test_files_dir, tmp_camels_dir)

    msg = "You have to specify a basin ID to be able to generate forcing from Caravan."
    with pytest.raises(ValueError, match=msg):
        CaravanForcing.generate(
            start_time="1981-01-01T00:00:00Z",
            end_time="1981-03-01T00:00:00Z",
            directory=str(tmp_camels_dir),
        )


def test_extract_basin_shapefile(tmp_path: Path):
    basin_id = "camels_01022500"
    test_files_dir = Path(__file__).parent / "forcing_files"
    tmp_camels_dir = tmp_path / "camels"
    copytree(test_files_dir, tmp_camels_dir)
    extracted_shape_file_dir = tmp_camels_dir / f"{basin_id}.shp"
    combined_shape_file_dir = tmp_camels_dir / "test_extract_basin_shapefile_data.shp"
    extract_basin_shapefile(basin_id, combined_shape_file_dir, extracted_shape_file_dir)

    shape_obj = shapereader.Reader(extracted_shape_file_dir)
    records = [rec for rec in shape_obj.records()]

    assert len(records) == 1
    assert records[0].attributes["gauge_id"] == basin_id
