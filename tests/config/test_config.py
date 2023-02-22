from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import ValidationError

from ewatercycle import CFG
from ewatercycle.config._config_object import Configuration


def test_config_object():
    """Test that the config is of the right type."""
    assert isinstance(CFG, Configuration)


def test_singularity_dir_is_deprecated(tmp_path):
    with pytest.warns(
        DeprecationWarning, match="singularity_dir field has been deprecated"
    ):
        config = Configuration(**{"singularity_dir": tmp_path})

        assert config.apptainer_dir == tmp_path
        assert config.singularity_dir is None


@pytest.fixture
def example_grdc_location(tmp_path):
    grdc_location = tmp_path / "grdc"
    grdc_location.mkdir()
    return grdc_location


@pytest.fixture
def example_config_file(tmp_path, example_grdc_location):
    config_file = tmp_path / "ewatercycle.yaml"
    config_file.write_text(
        dedent(
            f"""\
        grdc_location: {example_grdc_location}
        """
        )
    )
    return config_file


def test_load_from_file(example_grdc_location, example_config_file):
    config = Configuration()

    config.load_from_file(example_config_file)

    expected = Configuration(
        grdc_location=example_grdc_location, ewatercycle_config=example_config_file
    )
    assert config == expected


def test_load_from_file_given_bad_path():
    config_file = Path("/path/that/does/not/exist")
    config = Configuration()

    with pytest.raises(FileNotFoundError):
        config.load_from_file(config_file)


def test_load_from_file_bad_path_returns_eror_with_config_file_in_loc(tmp_path):
    config = Configuration()
    config_file = tmp_path / "ewatercycle.yaml"
    config_file.write_text(
        dedent(
            f"""\
        grdc_location: /a/directory/that/does/not/exist
        """
        )
    )

    with pytest.raises(ValidationError) as exc_info:
        config.load_from_file(config_file)

    errors = exc_info.value.errors()
    expected = [
        {
            "ctx": {"path": "/a/directory/that/does/not/exist"},
            "loc": (f"{config_file}:grdc_location",),
            "msg": 'file or directory at path "/a/directory/that/does/not/exist" does not exist',
            "type": "value_error.path.not_exists",
        }
    ]
    assert errors == expected


def test_reload_from_default(tmp_path):
    config = Configuration()
    config.grdc_location = tmp_path

    config.reload()

    assert config.grdc_location == Path(".")


def test_reload_from_file(tmp_path, example_grdc_location, example_config_file):
    config = Configuration(ewatercycle_config=example_config_file)
    config.grdc_location = tmp_path

    config.reload()

    assert config.grdc_location == example_grdc_location


def test_save_to_file_given_path(tmp_path: Path):
    config = Configuration()
    config_file = tmp_path / "ewatercycle.yaml"

    config.save_to_file(config_file)

    content = config_file.read_text()
    expected = dedent(
        """\
        apptainer_dir: .
        container_engine: docker
        grdc_location: .
        output_dir: .
        parameter_sets: {}
        parameterset_dir: .
        """
    )
    assert content == expected


def test_dump_to_yaml():
    config = Configuration()
    content = config.dump_to_yaml()

    expected = dedent(
        """\
        apptainer_dir: .
        container_engine: docker
        grdc_location: .
        output_dir: .
        parameter_sets: {}
        parameterset_dir: .
        """
    )
    assert content == expected


def test_prepend_root_to_parameterset_paths_given_relative_paths(tmp_path: Path):
    parameterset_dir = tmp_path / "psr"
    parameterset_dir.mkdir()
    ps1_dir = parameterset_dir / "ps1"
    ps1_dir.mkdir()
    ps1_config = ps1_dir / "config.ini"
    ps1_config.write_text("something")
    parameter_sets = {"ps1": {"directory": "ps1", "config": "ps1/config.ini"}}

    config = Configuration(
        parameterset_dir=parameterset_dir, parameter_sets=parameter_sets
    )

    ps1 = config.parameter_sets["ps1"]
    assert ps1.directory == ps1_dir
    assert ps1.config == ps1_config


def test_prepend_root_to_parameterset_paths_given_absolute_paths(tmp_path: Path):
    parameterset_dir = tmp_path / "psr"
    parameterset_dir.mkdir()
    ps1_dir = parameterset_dir / "ps1"
    ps1_dir.mkdir()
    ps1_config = ps1_dir / "config.ini"
    ps1_config.write_text("something")
    parameter_sets = {
        "ps1": {
            "directory": str(ps1_dir.absolute()),
            "config": str(ps1_config.absolute()),
        }
    }

    config = Configuration(
        parameterset_dir=parameterset_dir, parameter_sets=parameter_sets
    )

    ps1 = config.parameter_sets["ps1"]
    assert ps1.directory == ps1_dir
    assert ps1.config == ps1_config
