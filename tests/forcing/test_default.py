import logging
import pytest

from ewatercycle.forcing import generate, load_foreign, DefaultForcing, load, FORCING_YAML


def test_generate_unknown_model(sample_shape):
    with pytest.raises(NotImplementedError):
        generate(
            target_model="unknown",
            dataset='ERA5',
            start_time='1989-01-02T00:00:00Z',
            end_time='1999-01-02T00:00:00Z',
            shape=sample_shape
        )


def test_load_foreign_unknown():
    with pytest.raises(NotImplementedError) as excinfo:
        load_foreign(
            target_model='unknown',
            directory='/data/unknown-forcings-case1',
            start_time='1989-01-02T00:00:00Z',
            end_time='1999-01-02T00:00:00Z'
        )
    assert 'Target model `unknown` is not supported by the eWatercycle forcing generator' in str(excinfo.value)


@pytest.fixture
def sample_forcing_yaml_content():
    return ''.join([
        '!DefaultForcing\n',
        "start_time: '1989-01-02T00:00:00Z'\n",
        "end_time: '1999-01-02T00:00:00Z'\n",
        "shape:\n"
    ])

@pytest.fixture
def sample_forcing_yaml_content_with_shape():
    return ''.join([
        '!DefaultForcing\n',
        "start_time: '1989-01-02T00:00:00Z'\n",
        "end_time: '1999-01-02T00:00:00Z'\n",
        "shape: myshape.shp\n"
    ])

def test_save_with_shapefile_outside_forcing_dir(sample_shape, tmp_path, sample_forcing_yaml_content, caplog):
    forcing = DefaultForcing(
        directory=str(tmp_path),
        start_time='1989-01-02T00:00:00Z',
        end_time='1999-01-02T00:00:00Z',
        shape=sample_shape
    )
    with caplog.at_level(logging.INFO):
        forcing.save()

    file = tmp_path / FORCING_YAML
    written = file.read_text()
    expected = sample_forcing_yaml_content
    assert written == expected
    assert 'is not in forcing directory' in caplog.text

def test_save_with_shapefile_inside_forcing_dir(tmp_path, sample_forcing_yaml_content_with_shape, caplog):

    forcing = DefaultForcing(
        directory=str(tmp_path),
        start_time='1989-01-02T00:00:00Z',
        end_time='1999-01-02T00:00:00Z',
        shape=str(tmp_path / "myshape.shp")
    )
    with caplog.at_level(logging.INFO):
        forcing.save()

    file = tmp_path / FORCING_YAML
    written = file.read_text()
    expected = sample_forcing_yaml_content_with_shape
    assert written == expected
    assert 'is not in forcing directory' not in caplog.text


def test_save_without_shapefile(tmp_path, sample_forcing_yaml_content):

    forcing = DefaultForcing(
        directory=str(tmp_path),
        start_time='1989-01-02T00:00:00Z',
        end_time='1999-01-02T00:00:00Z',
    )
    forcing.save()

    file = tmp_path / FORCING_YAML
    written = file.read_text()
    expected = sample_forcing_yaml_content
    assert written == expected


def test_load(tmp_path, sample_forcing_yaml_content):
    file = tmp_path / FORCING_YAML
    file.write_text(sample_forcing_yaml_content)
    result = load(tmp_path)
    expected = DefaultForcing(
        directory=str(tmp_path),
        start_time='1989-01-02T00:00:00Z',
        end_time='1999-01-02T00:00:00Z',
    )
    assert result == expected


def test_load_with_shape(tmp_path, sample_forcing_yaml_content_with_shape):
    file = tmp_path / FORCING_YAML
    file.write_text(sample_forcing_yaml_content_with_shape)
    result = load(tmp_path)
    expected = DefaultForcing(
        directory=str(tmp_path),
        start_time='1989-01-02T00:00:00Z',
        end_time='1999-01-02T00:00:00Z',
        shape=tmp_path / "myshape.shp"

    )
    assert result == expected


def test_load_without_yaml(tmp_path):
    with pytest.raises(FileNotFoundError) as excinfo:
        load(tmp_path)
    assert str(tmp_path / FORCING_YAML) in str(excinfo.value)
