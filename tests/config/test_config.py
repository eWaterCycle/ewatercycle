from pathlib import Path
from textwrap import dedent

import pytest

from ewatercycle import CFG
from ewatercycle.config._config_object import Config


def test_config_object():
    """Test that the config is of the right type."""
    assert isinstance(CFG, Config)


def test_singularity_dir_is_deprecated(tmp_path):
    with pytest.warns(
        DeprecationWarning, match="ingularity_dir field has been deprecated"
    ):
        config = Config(**{"singularity_dir": str(tmp_path)})

        assert config.apptainer_dir == tmp_path


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
    config = Config()

    config.load_from_file(example_config_file)

    expected = Config(
        grdc_location=example_grdc_location, ewatercycle_config=example_config_file
    )
    assert config == expected


def test_load_from_file_given_bad_path():
    config_file = Path("/path/that/does/not/exist")
    config = Config()

    with pytest.raises(FileNotFoundError):
        config.load_from_file(config_file)


def test_reload_from_default(tmp_path):
    config = Config()
    config.grdc_location = tmp_path

    config.reload()

    assert config.grdc_location is None


def test_reload_from_file(tmp_path, example_grdc_location, example_config_file):
    config = Config(ewatercycle_config=example_config_file)
    config.grdc_location = tmp_path

    config.reload()

    assert config.grdc_location == example_grdc_location


def test_save_to_file_given_path(tmp_path: Path):
    config = Config()
    config_file = tmp_path / "ewatercycle.yaml"

    config.save_to_file(config_file)

    content = config_file.read_text()
    expected = dedent(
        """\
        apptainer_dir: null
        container_engine: docker
        grdc_location: null
        output_dir: null
        parameter_sets: {}
        parameterset_dir: null
        singularity_dir: null
        """
    )
    assert content == expected


def test_dump_to_yaml():
    config = Config()
    content = config.dump_to_yaml()

    expected = dedent(
        """\
        apptainer_dir: null
        container_engine: docker
        grdc_location: null
        output_dir: null
        parameter_sets: {}
        parameterset_dir: null
        singularity_dir: null
        """
    )
    assert content == expected
