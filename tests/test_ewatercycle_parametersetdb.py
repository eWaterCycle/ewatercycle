#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the ewatercycle_parametersetdb module.
"""
import pytest

from ewatercycle_parametersetdb import ewatercycle_parametersetdb


def test_without_test_object():
    assert False


class TestEwatercycle_parametersetdb(object):
    @pytest.fixture
    def return_a_test_object(self):
        pass

    def test_ewatercycle_parametersetdb(self, ewatercycle_parametersetdb):
        assert False

    def test_with_error(self, ewatercycle_parametersetdb):
        with pytest.raises(ValueError):
            pass
