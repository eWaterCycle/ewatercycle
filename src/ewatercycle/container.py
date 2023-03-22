"""Container utilities."""
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Union

from bmipy import Bmi
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_apptainer import BmiClientApptainer
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_memoized import MemoizedBmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi

from ewatercycle.config import CFG, ContainerEngine

ImageForContainerEngines = Dict[ContainerEngine, str]
"""Container image name for each container engine."""

VersionImages = Mapping[str, ImageForContainerEngines]
"""Dictionary of versions of a model.

Each version has the image name for each container engine.
"""


def start_container(
    work_dir: Union[str, Path],
    image_engine: ImageForContainerEngines,
    input_dirs: Optional[Iterable[str]] = None,
    image_port=55555,
    timeout=None,
    delay=0,
) -> Bmi:
    """Start container with model inside.

    The
    :attr:`CFG.container_engine <ewatercycle.config.Configuration.container_engine>`
    value determines the engine used to start a container.

    Args:
        work_dir: Work directory
        image_engine: Image name for each container engine.
        input_dirs: Additional directories to mount inside container.
        image_port: Docker port inside container where grpc4bmi server is running.
        timeout: Number of seconds to wait for grpc connection.
        delay: Number of seconds to wait before connecting.

    Raises:
        ValueError: When unknown container technology is requested.
        TimeoutError: When model inside container did not start quickly enough.

    Returns:
        Bmi object which wraps the container,
        has memoization and has optional dest arguments.

    Example:

        Given CFG.container_engine == docker a marrmot container can be started with::

            from ewatercycle.container import start_container

            model = start_container(
                work_dir='.',
                image_engine={
                    "docker": "ewatercycle/marrmot-grpc4bmi",
                }
            )
    """
    engine: ContainerEngine = CFG.container_engine
    image = image_engine[engine]
    if input_dirs is None:
        input_dirs = []
    if engine == "docker":
        bmi = start_docker_container(
            work_dir, image, input_dirs, image_port, timeout, delay
        )
    elif engine == "apptainer":
        docker_image = image_engine["docker"]
        bmi = start_apptainer_container(
            work_dir,
            image,
            docker_image,
            input_dirs,
            timeout,
            delay,
        )
    else:
        raise ValueError(f"Unknown container technology: {CFG.container_engine}")
    return OptionalDestBmi(MemoizedBmi(bmi))


def start_apptainer_container(
    work_dir: Union[str, Path],
    image: str,
    docker_image: str,
    input_dirs: Optional[Iterable[str]] = None,
    timeout: int = None,
    delay: int = 0,
) -> Bmi:
    """Start Apptainer container with model inside.

    Args:
        work_dir: Work directory
        image: Name of apptainer image.
            See `apptainer manual`_ for format.
        docker_image: Name of Docker image.
            Used in potential error message to instruct how to
            build an Apptainer image from a Docker image.
        input_dirs: Additional directories to mount inside container.
        timeout: Number of seconds to wait for grpc connection.
        delay: Number of seconds to wait before connecting.

    .. _apptainer manual: https://apptainer.org/docs/user/latest/cli/apptainer_run.html

    Raises:
        TimeoutError: When model inside container did not start quickly enough.

    Returns:
        Bmi object which wraps the container.
    """
    if (CFG.apptainer_dir / image).exists():
        image = str(CFG.apptainer_dir / image)
    try:
        return BmiClientApptainer(
            image=image,
            work_dir=str(work_dir),
            input_dirs=input_dirs,
            timeout=timeout,
            delay=delay,
        )
    except FutureTimeoutError as exc:
        raise TimeoutError(
            "Couldn't spawn container within allocated time limit "
            f"({timeout} seconds). You may try pulling the docker image with"
            f" `apptainer build {image} "
            f"docker://{docker_image}` and then try again."
        ) from exc


def start_docker_container(
    work_dir: Union[str, Path],
    image: str,
    input_dirs: Optional[Iterable[str]],
    image_port=55555,
    timeout=None,
    delay=0,
):
    """Start Docker container with model inside.

    Args:
        work_dir: Work directory
        image: Name of Docker image.
        input_dirs: Additional directories to mount inside container.
        image_port: Docker port inside container where grpc4bmi server is running.
        timeout: Number of seconds to wait for grpc connection.
        delay: Number of seconds to wait before connecting.

    Raises:
        TimeoutError: When model inside container did not start quickly enough.

    Returns:
        Bmi object which wraps the container.
    """
    try:
        return BmiClientDocker(
            image=image,
            image_port=image_port,
            work_dir=str(work_dir),
            input_dirs=input_dirs,
            timeout=timeout,
            delay=delay,
        )
    except FutureTimeoutError as exc:
        # https://github.com/eWaterCycle/grpc4bmi/issues/95
        # https://github.com/eWaterCycle/grpc4bmi/issues/100
        raise TimeoutError(
            "Couldn't spawn container within allocated time limit "
            f"({timeout} seconds). You may try pulling the docker image with"
            f" `docker pull {image}` and then try again."
        ) from exc
