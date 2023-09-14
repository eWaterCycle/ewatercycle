
from pathlib import Path
from unittest.mock import MagicMock, Mock
from grpc4bmi.bmi_optionaldest import OptionalDestBmi
from pytest import fixture

from ewatercycle.base.model import eWaterCycleModel
from ewatercycle.testing.fake_models import FailingModel

class MockBmi(FailingModel):
    def __init__(self):
        self._mock = Mock()
        super().__init__()

    def initialize(self, config_file: str) -> None:
        self._mock.initialize(config_file)

    def finalize(self):
        # TODO check if this is called
        pass

    def update(self):
        self._mock.update()

    def __eq__(self, __value: object) -> bool:
        return isinstance(__value, MockBmi)

class MockModel(eWaterCycleModel):

    def _make_bmi_instance(self):
        return OptionalDestBmi(MockBmi())

    
@fixture
def mocked_model(mocked_config):
    return MockModel()

def test_version(mocked_model: eWaterCycleModel):
    assert mocked_model.version == ""

def test_parameters(mocked_model: eWaterCycleModel):
    assert mocked_model.parameters == {}

class TestSetupWithCfgDir:
    @fixture(autouse=True)
    def setup_on_mocked_model(self, mocked_model: eWaterCycleModel, tmp_path: Path):
        return mocked_model.setup(cfg_dir=str(tmp_path))
    
    def test_cfg_dir(self, setup_on_mocked_model, tmp_path: Path):
        assert setup_on_mocked_model[1] == str(tmp_path)

    def test_cfg_file(self, setup_on_mocked_model, tmp_path: Path):
        expected = str(tmp_path / "config.yaml")
        assert setup_on_mocked_model[0] == expected

    def test_cfg_file_content(self, setup_on_mocked_model, tmp_path: Path):
        expected = '{}'
        assert (tmp_path / "config.yaml").read_text().strip() == expected

    def test_bmi(self, mocked_model: eWaterCycleModel):
        assert mocked_model.bmi.origin == MockBmi()

    def test_initialize(self, mocked_model: eWaterCycleModel, setup_on_mocked_model):
        config_file = setup_on_mocked_model[0]

        mocked_model.initialize(config_file)

        mocked_model.bmi.origin._mock.initialize.assert_called_once_with(config_file)

    def test_finalize(self, mocked_model: eWaterCycleModel):
        mocked_model.finalize()

        assert not hasattr(mocked_model, '_bmi')

    def test_update(self, mocked_model: eWaterCycleModel):
        mocked_model.update()

        mocked_model.bmi.origin._mock.update.assert_called_once_with()