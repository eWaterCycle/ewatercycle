"""Container utilities."""
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Union

from bmipy import Bmi
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_apptainer import BmiClientApptainer
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

    The `ewatercycle.'CFG.container_engine` value determines
    the engine used to start a container.

    Args:
        work_dir: Work directory
        version_image: Image name for each container engine.
        input_dirs: Additional directories to mount inside container.
        image_port: Docker port inside container where grpc4bmi server is running.
        timeout: Number of seconds to wait for grpc connection.
        delay: Number of seconds to wait before connecting.

    Raises:
        ValueError: When unknown container technology is requested.
        TimeoutError: When model inside container did not start quickly enough.

    Returns:
        _description_
    """
    engine: ContainerEngine = CFG.container_engine
    image = image_engine[engine]
    if input_dirs is None:
        input_dirs = []
    if engine == "docker":
        try:
            bmi = BmiClientDocker(
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
    elif engine == "apptainer":
        image = str(CFG.apptainer_dir / image)
        try:
            bmi = BmiClientApptainer(
                image=image,
                work_dir=str(work_dir),
                input_dirs=input_dirs,
                timeout=timeout,
                delay=delay,
            )
        except FutureTimeoutError as exc:
            docker_image = image_engine["docker"]
            raise TimeoutError(
                "Couldn't spawn container within allocated time limit "
                f"({timeout} seconds). You may try pulling the docker image with"
                f" `apptainer build {image} "
                f"docker://{docker_image}` and then try again."
            ) from exc
    else:
        raise ValueError(f"Unknown container technology: {CFG.container_engine}")
    return OptionalDestBmi(MemoizedBmi(bmi))
