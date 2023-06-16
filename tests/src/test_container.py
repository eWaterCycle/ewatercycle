import pytest

from ewatercycle.container import ContainerImage, _parse_docker_url

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
