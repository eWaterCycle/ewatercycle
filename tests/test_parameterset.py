# -*- coding: utf-8 -*-
from unittest import mock

from ewatercycle.parametersetdb import build_from_urls, ParameterSet
from ewatercycle.parametersetdb.datafiles import SubversionCopier


def test_build_from_urls(yaml_config_url, yaml_config):
    pset = build_from_urls(
        config_format='yaml', config_url=yaml_config_url,
        datafiles_format='svn', datafiles_url='http://example.com',
    )

    assert isinstance(pset.df, SubversionCopier)
    assert pset.config == yaml_config


class TestParameterSet:
    def test_save_config(self, sample_parameterset: ParameterSet, tmpdir):
        fn = tmpdir.join('myconfig.yml')

        sample_parameterset.save_config(str(fn))

        assert 'PEQ_Hupsel.dat' in fn.read()

    @mock.patch('subprocess.check_call')
    def test_save_datafiles(self, mock_check_call, sample_parameterset: ParameterSet):
        fn = '/somewhere/adirectory'

        sample_parameterset.save_datafiles(fn)

        expected_args = ['svn', 'export', sample_parameterset.df.source, fn]
        mock_check_call.assert_called_once_with(expected_args)
