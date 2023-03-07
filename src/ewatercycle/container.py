"""Container utilities."""
from pathlib import Path
from typing import Iterable, Literal, Mapping, Optional, TypedDict, Union

from bmipy import Bmi
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_client_singularity import BmiClientSingularity
from grpc4bmi.bmi_memoized import MemoizedBmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi

from ewatercycle import CFG


class VersionImage(TypedDict):
    """Image container for each container technology."""

    docker: str
    """Docker image name."""
    singularity: str
    """Singularity image name. Should be *.sif file in CFG["singularity_dir"]."""


VersionImages = Mapping[str, VersionImage]
"""Image containers for each version."""


def start_container(
    work_dir: Union[str, Path],
    version_image: VersionImage,
    input_dirs: Optional[Iterable[str]] = None,
    image_port=55555,
    timeout=None,
    delay=0,
) -> Bmi:
    """Start container with model inside.

    The `ewatercycle.CFG['container_engine']` value determines
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
    engine: Literal["docker", "singularity"] = CFG["container_engine"]
    image = version_image[engine]
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
                "({timeout} seconds). You may try pulling the docker image with"
                f" `docker pull {image}` and then try again."
            ) from exc
    elif engine == "singularity":
        image = CFG["singularity_dir"] / image
        try:
            bmi = BmiClientSingularity(
                image=image,
                work_dir=str(work_dir),
                input_dirs=input_dirs,
                timeout=timeout,
                delay=delay,
            )
        except FutureTimeoutError as exc:
            docker_image = version_image["docker"]
            raise TimeoutError(
                "Couldn't spawn container within allocated time limit "
                "({timeout} seconds). You may try pulling the docker image with"
                f" `singularity build {image} "
                f"docker://{docker_image}` and then try again."
            ) from exc
    else:
        raise ValueError(f"Unknown container technology: {CFG['container_engine']}")
    return OptionalDestBmi(MemoizedBmi(bmi))
