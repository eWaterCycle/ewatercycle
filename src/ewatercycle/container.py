"""Container utilities."""
import re
from pathlib import Path
from typing import Iterable, Optional, Union

from bmipy import Bmi
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_apptainer import BmiClientApptainer
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_memoized import MemoizedBmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi

from ewatercycle.config import CFG, ContainerEngine


class ContainerImage:
    """Utility for storing container images regardless of the container engine.

    Given a docker url with the following structure

        <repository>/<organisation>/<image_name>:<version>

    The corresponding apptainer filename is assumed to be

        <organisation>-<image_name>_<version>.sif

    The repository in the docker url is optional.

    Conversion from docker to apptainer is always possible
    Conversion from apptainer can lead to unexpected behaviour in some cases:
        - when image name contains '_' but no version tag
        - when image name contains '-' but no organisation

    eWatercycle containers typically don't have these issues.
    """

    def __init__(self, image):
        self.image: str = image

    @property
    def apptainer_filename(self) -> str:
        if self.image.endswith(".sif"):
            return self.image
        else:
            return self._as_apptainer_filename(self.image)

    @property
    def docker_url(self) -> str:
        if self.image.endswith(".sif"):
            return self._as_docker_url(self.image)
        else:
            return self.image

    def _parse_docker_url(self, docker_url):
        """Extract repository, image name and tag from docker url.

        Regex source: https://regex101.com/library/a98UqN
        """
        pattern = "^(?P<repository>[\w.\-_]+((?::\d+|)(?=/[a-z0-9._-]+/[a-z0-9._-]+))|)(?:/|)(?P<image>[a-z0-9.\-_]+(?:/[a-z0-9.\-_]+|))(:(?P<tag>[\w.\-_]{1,127})|)$"

        match = re.search(pattern, docker_url)

        if not match:
            raise ValueError(f"Unable to parse docker url: {docker_url}")

        repository = match.group("repository")
        image = match.group("image")
        tag = match.group("tag")

        return repository, image, tag

    def _as_apptainer_filename(self, docker_url):
        """Derive apptainer image filename from docker url."""
        _, image, tag = self._parse_docker_url(docker_url)

        apptainer_name = image.replace("/", "-")

        if tag:
            apptainer_name += f"_{tag}"

        apptainer_name += ".sif"

        return apptainer_name

    def _as_docker_url(self, apptainer_name):
        """Attempt to reconstruct docker url from singularity filename."""
        name = apptainer_name.replace(".sif", "")

        tag = ""
        if "_" in name:
            name, _, tag = name.rpartition("_")
            name += ":"

        organisation = ""
        if "-" in name:
            organisation, _, name = name.partition("-")
            organisation += "/"

        docker_url = organisation + name + tag
        return docker_url


def start_container(
    work_dir: Union[str, Path],
    image: ContainerImage,
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
        image: Image name for container.
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
                image="ewatercycle/marrmot-grpc4bmi",
            )
    """
    engine: ContainerEngine = CFG.container_engine
    if input_dirs is None:
        input_dirs = []

    if engine == "docker":
        bmi = start_docker_container(
            work_dir, image, input_dirs, image_port, timeout, delay
        )
    elif engine == "apptainer":
        bmi = start_apptainer_container(
            work_dir,
            image,
            input_dirs,
            timeout,
            delay,
        )
    else:
        raise ValueError(f"Unknown container technology: {CFG.container_engine}")
    return OptionalDestBmi(MemoizedBmi(bmi))


def start_apptainer_container(
    work_dir: Union[str, Path],
    image: ContainerImage,
    input_dirs: Optional[Iterable[str]] = None,
    timeout: Optional[int] = None,
    delay: int = 0,
) -> Bmi:
    """Start Apptainer container with model inside.

    Args:
        work_dir: Work directory
        image: Name of apptainer (sif file) or docker image (url).
            If a docker url is passed, will try to derive the apptainer filename
            following the format specified in `apptainer manual`_.
        input_dirs: Additional directories to mount inside container.
        timeout: Number of seconds to wait for grpc connection.
        delay: Number of seconds to wait before connecting.

    .. _apptainer manual: https://apptainer.org/docs/user/latest/cli/apptainer_run.html

    Raises:
        TimeoutError: When model inside container did not start quickly enough.

    Returns:
        Bmi object which wraps the container.
    """
    image_fn = image.apptainer_filename
    if (CFG.apptainer_dir / image_fn).exists():
        image_fn = str(CFG.apptainer_dir / image_fn)

    try:
        return BmiClientApptainer(
            image=image_fn,
            work_dir=str(work_dir),
            input_dirs=tuple() if input_dirs is None else input_dirs,
            timeout=timeout,
            delay=delay,
        )
    except FutureTimeoutError as exc:
        raise TimeoutError(
            "Couldn't spawn container within allocated time limit "
            f"({timeout} seconds). You may try pulling the docker image with"
            f" `apptainer build {image_fn} "
            f"docker://{image.docker_url}` and then try again."
        ) from exc


def start_docker_container(
    work_dir: Union[str, Path],
    image: ContainerImage,
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
            image=image.docker_url,
            image_port=image_port,
            work_dir=str(work_dir),
            input_dirs=tuple() if input_dirs is None else input_dirs,
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
