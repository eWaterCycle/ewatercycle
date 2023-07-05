from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from grpc4bmi.bmi_memoized import MemoizedBmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi
from numpy.testing import assert_array_almost_equal

from ewatercycle.config import CFG
from ewatercycle.container import BmiProxy, start_container
from tests.src.fake_models import Rect3DGridModel


def npeq(a, b):
    assert_array_almost_equal(a, b)


def eq(a, b):
    assert a == b


@pytest.mark.parametrize(
    "orig_model, method_name, method_args, assert_func",
    [
        [
            Rect3DGridModel(),
            "get_grid_shape",
            (0, np.zeros((3,))),
            lambda r: npeq(r, np.array([2, 3, 4])),
        ],
        [
            Rect3DGridModel(),
            "get_grid_rank",
            (0,),
            lambda r: eq(r, 3),
        ],
        [
            Rect3DGridModel(),
            "get_grid_size",
            (0,),
            lambda r: eq(r, 24),
        ],
        [
            Rect3DGridModel(),
            "get_var_grid",
            ("air__temperature",),
            lambda r: eq(r, 0),
        ],
        [
            Rect3DGridModel(),
            "get_grid_x",
            (0, np.empty((4,))),
            lambda r: npeq(r, np.array([0.1, 0.2, 0.3, 0.4])),
        ],
        [
            Rect3DGridModel(),
            "get_grid_y",
            (0, np.empty((3,))),
            lambda r: npeq(r, np.array([1.1, 1.2, 1.3])),
        ],
        [
            Rect3DGridModel(),
            "get_grid_z",
            (0, np.empty((2,))),
            lambda r: npeq(r, np.array([2.1, 2.2])),
        ],
    ],
)
def test_bmi_proxy(orig_model, method_name, method_args, assert_func):
    orig_model = Rect3DGridModel()
    model = BmiProxy(orig_model)

    method = getattr(model, method_name)
    result = method(*method_args)

    assert_func(result)


@pytest.fixture
def force_apptainer(tmp_path: Path):
    old_engine = CFG.container_engine
    old_dir = CFG.apptainer_dir
    CFG.container_engine = "apptainer"
    CFG.apptainer_dir = tmp_path
    yield {"docker": "dummyimage:latest", "apptainer": "dummyimage.sif"}
    CFG.container_engine = old_engine
    CFG.apptainer_dir = old_dir


@pytest.fixture
def mock_bmi_client_apptainer():
    with mock.patch("ewatercycle.container.BmiClientApptainer") as mock_class:
        mock_class.return_value = Rect3DGridModel()
        yield mock_class


# Test the start_container function with the mocked BmiClientApptainer class
def test_start_container(
    tmp_path: Path, force_apptainer, mock_bmi_client_apptainer: mock.MagicMock
):
    container = start_container(work_dir=tmp_path, image_engine=force_apptainer)

    assert isinstance(container, OptionalDestBmi)
    assert isinstance(container.origin, MemoizedBmi)
    assert isinstance(container.origin.origin, Rect3DGridModel)
    mock_bmi_client_apptainer.assert_called_once_with(
        image=force_apptainer["apptainer"],
        work_dir=str(tmp_path),
        timeout=None,
        delay=0,
        input_dirs=[],
    )


def test_start_container_without_wrapper(
    tmp_path: Path, force_apptainer, mock_bmi_client_apptainer: mock.MagicMock
):
    container = start_container(
        work_dir=tmp_path, image_engine=force_apptainer, wrappers=[]
    )
    assert isinstance(container, Rect3DGridModel)


def test_start_container_with_own_wrapper(
    tmp_path: Path, force_apptainer, mock_bmi_client_apptainer: mock.MagicMock
):
    class MyWrapper(BmiProxy):
        pass

    container = start_container(
        work_dir=tmp_path, image_engine=force_apptainer, wrappers=(MyWrapper,)
    )

    assert isinstance(container, MyWrapper)
    assert isinstance(container.origin, Rect3DGridModel)
