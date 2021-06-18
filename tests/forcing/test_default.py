import pytest

from ewatercycle.forcing import generate, load_foreign


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
