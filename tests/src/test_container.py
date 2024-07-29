from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from grpc4bmi.bmi_memoized import MemoizedBmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi
from numpy.testing import assert_array_almost_equal

from ewatercycle.config import CFG
from ewatercycle.container import (
    BmiProxy,
    ContainerImage,
    _parse_docker_url,
    start_container,
)
from ewatercycle.testing.fake_models import DummyModelWith2DRectilinearGrid

images = [
    (
        "ewatercycle-pcrg-grpc4bmi_setters.sif",
        "ewatercycle/pcrg-grpc4bmi:setters",
    ),
    (
        "ewatercycle-wflow-grpc4bmi_2019.1.sif",
        "ewatercycle/wflow-grpc4bmi:2019.1",
    ),
    (
        "ewatercycle-wflow-grpc4bmi_2020.1.1.sif",
        "ewatercycle/wflow-grpc4bmi:2020.1.1",
    ),
    (
        "ewatercycle-wflow-grpc4bmi_2020.1.2.sif",
        "ewatercycle/wflow-grpc4bmi:2020.1.2",
    ),
    (
        "ewatercycle-wflow-grpc4bmi_2020.1.3.sif",
        "ewatercycle/wflow-grpc4bmi:2020.1.3",
    ),
    (
        "ewatercycle-lisflood-grpc4bmi_20.10.sif",
        "ewatercycle/lisflood-grpc4bmi:20.10",
    ),
    (
        "ewatercycle-marrmot-grpc4bmi_2020.11.sif",
        "ewatercycle/marrmot-grpc4bmi:2020.11",
    ),
    (
        "ewatercycle-hype-grpc4bmi_feb2021.sif",
        "ewatercycle/hype-grpc4bmi:feb2021",
    ),
    (
        "ewatercycle-hype-grpc4bmi.sif",
        "ewatercycle/hype-grpc4bmi",
    ),
]


@pytest.mark.parametrize("apptainer_filename,docker_url", images)
def test_docker_to_apptainer(apptainer_filename, docker_url):
    assert ContainerImage(docker_url).apptainer_filename == apptainer_filename


@pytest.mark.parametrize("apptainer_filename,docker_url", images)
def test_apptainer_to_docker(apptainer_filename, docker_url):
    assert ContainerImage(apptainer_filename).docker_url == docker_url


@pytest.mark.parametrize("apptainer_filename,docker_url", images)
def test_return_self(apptainer_filename, docker_url):
    assert ContainerImage(apptainer_filename).apptainer_filename == apptainer_filename
    assert ContainerImage(docker_url).docker_url == docker_url


def test_apptainer_to_docker_invalid():
    with pytest.raises(ValueError):
        _parse_docker_url("not:url///nor::sif")


def test_with_repo():
    docker_url = "ghcr.io/ewatercycle/hype-grpc4bmi:feb2021"
    apptainer_filename = "ewatercycle-hype-grpc4bmi_feb2021.sif"
    result = ContainerImage(docker_url).apptainer_filename
    assert result == apptainer_filename

    # Can't infer repository in this case
    bare_docker_url = "ewatercycle/hype-grpc4bmi:feb2021"
    assert ContainerImage(apptainer_filename).docker_url == bare_docker_url


@pytest.mark.parametrize(
    "image,expected_version",
    [
        ["ghcr.io/ewatercycle/wflow:latest", "latest"],
        ["ewatercycle-wflow_latest.sif", "latest"],
        ["ghcr.io/ewatercycle/wflow:2020.1.4", "2020.1.4"],
        ["ewatercycle-wflow_2020.1.4.sif", "2020.1.4"],
        ["ghcr.io/ewatercycle/wflow", "unknown"],
        ["ewatercycle-wflow.sif", "unknown"],
    ],
)
def test_containerimage_version(image, expected_version):
    assert ContainerImage(image).version == expected_version


def npeq(a, b):
    assert_array_almost_equal(a, b)


def eq(a, b):
    assert a == b


@pytest.mark.parametrize(
    "orig_model, method_name, method_args, assert_func",
    [
        [
            DummyModelWith2DRectilinearGrid(),
            "get_grid_shape",
            (0, np.zeros((2,))),
            lambda r: npeq(r, np.array([3, 4])),
        ],
        [
            DummyModelWith2DRectilinearGrid(),
            "get_grid_rank",
            (0,),
            lambda r: eq(r, 2),
        ],
        [
            DummyModelWith2DRectilinearGrid(),
            "get_grid_size",
            (0,),
            lambda r: eq(r, 12),
        ],
        [
            DummyModelWith2DRectilinearGrid(),
            "get_var_grid",
            ("air__temperature",),
            lambda r: eq(r, 0),
        ],
        [
            DummyModelWith2DRectilinearGrid(),
            "get_grid_x",
            (0, np.empty((4,))),
            lambda r: npeq(r, np.array([0.1, 0.2, 0.3, 0.4])),
        ],
        [
            DummyModelWith2DRectilinearGrid(),
            "get_grid_y",
            (0, np.empty((3,))),
            lambda r: npeq(r, np.array([1.1, 1.2, 1.3])),
        ],
    ],
)
def test_bmi_proxy(orig_model, method_name, method_args, assert_func):
    orig_model = DummyModelWith2DRectilinearGrid()
    model = BmiProxy(orig_model)

    method = getattr(model, method_name)
    result = method(*method_args)

    assert_func(result)


@pytest.fixture()
def force_apptainer(tmp_path: Path):
    old_engine = CFG.container_engine
    old_dir = CFG.apptainer_dir
    CFG.container_engine = "apptainer"
    CFG.apptainer_dir = tmp_path
    yield ContainerImage("dummyimage:latest")
    CFG.container_engine = old_engine
    CFG.apptainer_dir = old_dir


@pytest.fixture()
def mock_bmi_client_apptainer():
    with mock.patch("ewatercycle.container.BmiClientApptainer") as mock_class:
        mock_class.return_value = DummyModelWith2DRectilinearGrid()
        yield mock_class


# Test the start_container function with the mocked BmiClientApptainer class
def test_start_container(
    tmp_path: Path, force_apptainer, mock_bmi_client_apptainer: mock.MagicMock
):
    container = start_container(work_dir=tmp_path, image=force_apptainer)

    assert isinstance(container, OptionalDestBmi)
    assert isinstance(container.origin, MemoizedBmi)
    assert isinstance(container.origin.origin, DummyModelWith2DRectilinearGrid)
    mock_bmi_client_apptainer.assert_called_once_with(
        image=force_apptainer.apptainer_filename,
        work_dir=str(tmp_path),
        timeout=None,
        delay=0,
        input_dirs=[],
    )


def test_start_container_without_wrapper(
    tmp_path: Path, force_apptainer, mock_bmi_client_apptainer: mock.MagicMock
):
    container = start_container(work_dir=tmp_path, image=force_apptainer, wrappers=[])
    assert isinstance(container, DummyModelWith2DRectilinearGrid)


def test_start_container_with_own_wrapper(
    tmp_path: Path, force_apptainer, mock_bmi_client_apptainer: mock.MagicMock
):
    class MyWrapper(BmiProxy):
        pass

    container = start_container(
        work_dir=tmp_path, image=force_apptainer, wrappers=(MyWrapper,)
    )

    assert isinstance(container, MyWrapper)
    assert isinstance(container.origin, DummyModelWith2DRectilinearGrid)
