from pathlib import Path
from shutil import copytree

from ewatercycle.base.forcing import FORCING_YAML, GenericDistributedForcing

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
