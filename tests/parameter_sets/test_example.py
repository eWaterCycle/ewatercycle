from io import StringIO, BytesIO
from unittest.mock import patch, Mock

import pytest

from ewatercycle import CFG
from ewatercycle.parameter_sets import ExampleParameterSet


@pytest.fixture
def setup_config(tmp_path):
    CFG['parameterset_dir'] = tmp_path
    yield CFG
    # Rollback changes made to CFG by tests
    CFG.reload()


class TestGoldenPath:
    @pytest.fixture
    def example(self, setup_config):
        return ExampleParameterSet(
            name='firstexample',
            config_url='https://github.com/mymodelorg/mymodelrepo/raw/master/mymodelexample/config.ini',
            datafiles_url='https://github.com/mymodelorg/mymodelrepo/trunk/mymodelexample',
            directory='mymodelexample',
            config='mymodelexample/config.ini',
            supported_model_versions={'0.4.2'},
        )

    def test_to_config(self, example):
        example.to_config()

        assert 'firstexample' in CFG['parameter_sets']
        expected = dict(
            doi='N/A',
            target_model='generic',
            directory='mymodelexample',
            config='mymodelexample/config.ini',
            supported_model_versions={'0.4.2'},
        )
        assert CFG['parameter_sets']['firstexample'] == expected

    @patch('urllib.request.urlopen')
    @patch('subprocess.check_call')
    def test_download(self, mock_check_call, mock_urlopen, example, tmp_path):
        ps_dir = tmp_path / 'mymodelexample'
        r = Mock()
        r.read.return_value = b'somecontent'
        mock_urlopen.return_value = r
        mock_check_call.side_effect = lambda _: ps_dir.mkdir()

        example.download()

        mock_urlopen.assert_called_once_with('https://github.com/mymodelorg/mymodelrepo/raw/master/mymodelexample/config.ini')
        mock_check_call.assert_called_once_with([
            'svn', 'export',
            'https://github.com/mymodelorg/mymodelrepo/trunk/mymodelexample',
            ps_dir
        ])
        assert (ps_dir / 'config.ini').read_text() == 'somecontent'

    def test_download_already_exists(self, example, tmp_path):
        ps_dir = tmp_path / 'mymodelexample'
        ps_dir.mkdir()

        with pytest.raises(ValueError) as excinfo:
            example.download()

        assert str(excinfo.value) == 'Directory already exists, will not overwrite'
