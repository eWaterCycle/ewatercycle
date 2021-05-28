import pytest
from ruamel.yaml import YAML

from ewatercycle.forcing import generate, load_foreign, DefaultForcing, load


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
    forcing = load_foreign(
        target_model='unknown',
        forcing_info={
            'directory': '/data/unknown-forcings-case1',
            'start_time': '1989-01-02T00:00:00Z',
            'end_time': '1999-01-02T00:00:00Z'
        }
    )
    expected = DefaultForcing(directory='/data/unknown-forcings-case1',
                              start_time='1989-01-02T00:00:00Z',
                              end_time='1999-01-02T00:00:00Z')
    assert forcing == expected


def test_save_load(tmp_path):
    forcing = load_foreign(
        target_model='unknown',
        forcing_info={
            'directory': str(tmp_path),
            'start_time': '1989-01-02T00:00:00Z',
            'end_time': '1999-01-02T00:00:00Z'
        }
    )
    forcing.save()

    saved_forcing = load(tmp_path)

    assert forcing == saved_forcing
