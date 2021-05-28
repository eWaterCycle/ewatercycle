"""Tests for the constructors in ewatercycle.forcing module."""

import ewatercycle.forcing
import pytest

def test_save_and_load_default_forcing(tmp_path):
    d = tmp_path / 'defaultforcing'
    d.mkdir()
    forcing = ewatercycle.forcing.default.DefaultForcing(
        start_time='20200101_0000',
        end_time='20200102_0000',
        directory=str(d))

    forcing.save()
    f = d / 'ewatercycle_forcing.yaml'
    assert f.exists()

    loaded_forcing = forcing.load(str(d))
    assert loaded_forcing == forcing
