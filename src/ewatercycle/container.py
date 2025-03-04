"""Container utilities."""
# ruff: noqa: D102
# ruff: noqa: D107

import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol

import numpy as np
import remotebmi
from bmipy import Bmi
from grpc import FutureTimeoutError
from grpc4bmi.bmi_client_apptainer import BmiClientApptainer
from grpc4bmi.bmi_client_docker import BmiClientDocker
from grpc4bmi.bmi_memoized import MemoizedBmi
from grpc4bmi.bmi_optionaldest import OptionalDestBmi

from ewatercycle.config import CFG, ContainerEngine


def _parse_docker_url(docker_url):
    """Extract repository, image name and tag from docker url.

    Regex source: https://regex101.com/library/a98UqN
    """
    pattern = re.compile(
        r"^(?P<repository>[\w.\-_]+((?::\d+|)"
        r"(?=/[a-z0-9._-]+/[a-z0-9._-]+))|)"
        r"(?:/|)"
        r"(?P<image>[a-z0-9.\-_]+(?:/[a-z0-9.\-_]+|))"
        r"(:(?P<tag>[\w.\-_]{1,127})|)$"
    )

    match = pattern.search(docker_url)

    if not match:
        msg = f"Unable to parse docker url: {docker_url}"
        raise ValueError(msg)

    repository = match.group("repository")
    image = match.group("image")
    tag = match.group("tag")

    return repository, image, tag


class ContainerImage(str):
    """Custom type for parsing and utilizing container images.

    Given a docker url with the following structure

        <repository>/<organisation>/<image_name>:<version>

    The corresponding apptainer filename is assumed to be

        <organisation>-<image_name>_<version>.sif

    The repository in the docker url is optional.

    Conversion from docker to apptainer is always possible
    Conversion from apptainer can lead to unexpected behaviour in some cases:

    * when image name contains '_' but no version tag
    * when image name contains '-' but no organisation

    eWatercycle containers typically don't have these issues.
    """

    __slots__ = ()

    def _validate(self):
        """Verify image ends with .sif or can parse as docker url."""
        if not self.endswith(".sif"):
            _parse_docker_url(self)

    @property
    def apptainer_filename(self) -> str:
        """Return self as apptainer filename."""
        if self.endswith(".sif"):
            return self

        # Derive apptainer image filename from docker url."""
        _, image, tag = _parse_docker_url(self)

        apptainer_name = image.replace("/", "-")

        if tag:
            apptainer_name += f"_{tag}"
        apptainer_name += ".sif"

        return apptainer_name

    @property
    def docker_url(self) -> str:
        """Return self as docker url."""
        if not self.endswith(".sif"):
            return self

        # Attempt to reconstruct docker url from singularity filename.
        name = self.replace(".sif", "")

        tag = ""
        if "_" in name:
            name, _, tag = name.rpartition("_")
            name += ":"

        organisation = ""
        if "-" in name:
            organisation, _, name = name.partition("-")
            organisation += "/"

        return organisation + name + tag

    @property
    def version(self) -> str:
        if self.endswith(".sif"):
            name = self.replace(".sif", "")
            if "_" in name:
                name, _, tag = name.rpartition("_")
                return tag
            return "unknown"

        # Get version tag from docker url
        _, _, tag = _parse_docker_url(self)
        if tag is not None:
            return tag
        return "unknown"


def start_container(
    work_dir: str | Path,
    image: ContainerImage,
    input_dirs: Iterable[str] | None = None,
    image_port=55555,
    timeout=None,
    delay=0,
    # TODO replace Any type with Bmi + BmiFromOrigin
    wrappers: Sequence[type[Any]] = (MemoizedBmi, OptionalDestBmi),
    protocol: Literal["grpc", "openapi"] = "grpc",
) -> OptionalDestBmi:
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
        wrappers: List of classes to wrap around the grcp4bmi object from container.
            Order is important. The first wrapper is the most inner wrapper.
        protocol: Which protocol to use, grpc or openapi.

    Raises:
        ValueError: When unknown container technology is requested.
        TimeoutError: When model inside container did not start quickly enough.

    Returns:
        When default wrappers are used then returns the
        :py:class:`Bmi object
        which wraps the container <grpc4bmi.bmi_grpc_client.BmiClient>`,
        has :py:class:`memoization <grpc4bmi.bmi_memoized.MemoizedBmi>` and
        has
        :py:class:`optional dest arguments <grpc4bmi.bmi_optionaldest.OptionalDestBmi>`
        .
        When no wrappers are used then returns the :py:class:`Bmi object
        which wraps the container <grpc4bmi.bmi_grpc_client.BmiClient>`.

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
            work_dir,
            image,
            input_dirs,
            image_port,
            timeout,
            delay,
            protocol,
        )
    elif engine == "apptainer":
        bmi = start_apptainer_container(
            work_dir,
            image,
            input_dirs,
            timeout,
            delay,
            protocol,
        )
    else:
        msg = f"Unknown container technology: {CFG.container_engine}"
        raise ValueError(msg)

    for wrapper in wrappers:
        bmi = wrapper(bmi)
    return bmi


def start_apptainer_container(
    work_dir: str | Path,
    image: ContainerImage,
    input_dirs: Iterable[str] = (),
    timeout: int | None = None,
    delay: int = 0,
    protocol: Literal["grpc", "openapi"] = "grpc",
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
        protocol: Which protocol to use, grpc or openapi.

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
        if protocol == "grpc":
            return BmiClientApptainer(
                image=image_fn,
                work_dir=str(work_dir),
                input_dirs=input_dirs,
                timeout=timeout,
                delay=delay,
            )
        if protocol == "openapi":
            return remotebmi.BmiClientApptainer(
                image=image_fn,
                work_dir=str(work_dir),
                input_dirs=input_dirs,
                delay=delay,
            )
        msg = f"Invalid protocol '{protocol}'!"
        raise ValueError(msg)

    except FutureTimeoutError as exc:
        msg = (
            "Couldn't spawn container within allocated time limit "
            f"({timeout} seconds). You may try pulling the docker image with"
            f" `apptainer build {image_fn} "
            f"docker://{image.docker_url}` and then try again."
        )
        raise TimeoutError(msg) from exc


def start_docker_container(
    work_dir: str | Path,
    image: ContainerImage,
    input_dirs: Iterable[str] = (),
    image_port=55555,
    timeout=None,
    delay=0,
    protocol: Literal["grpc", "openapi"] = "grpc",
):
    """Start Docker container with model inside.

    Args:
        work_dir: Work directory
        image: Name of Docker image.
        input_dirs: Additional directories to mount inside container.
        image_port: Docker port inside container where grpc4bmi server is running.
        timeout: Number of seconds to wait for grpc connection.
        delay: Number of seconds to wait before connecting.
        protocol: Which protocol to use, grpc or openapi.

    Raises:
        TimeoutError: When model inside container did not start quickly enough.

    Returns:
        Bmi object which wraps the container.
    """
    try:
        if protocol == "grpc":
            return BmiClientDocker(
                image=image.docker_url,
                image_port=image_port,
                work_dir=str(work_dir),
                input_dirs=input_dirs,
                timeout=timeout,
                delay=delay,
            )
        if protocol == "openapi":
            return remotebmi.BmiClientDocker(
                image=image.docker_url,
                host="localhost",
                image_port=50051,
                work_dir=str(work_dir),
                input_dirs=input_dirs,
                delay=delay,
            )
        msg = f"Invalid protocol '{protocol}'!"
        raise ValueError(msg)
    except FutureTimeoutError as exc:
        # https://github.com/eWaterCycle/grpc4bmi/issues/95
        # https://github.com/eWaterCycle/grpc4bmi/issues/100
        msg = (
            "Couldn't spawn container within allocated time limit "
            f"({timeout} seconds). You may try pulling the docker image with"
            f" `docker pull {image}` and then try again."
        )
        raise TimeoutError(msg) from exc


class BmiFromOrigin(Protocol):
    """Protocol for a BMI that can be used as a BMI itself."""

    def __init__(self, origin: Bmi):
        pass


class BmiProxy(Bmi):
    """Proxy for a BMI that can be used as a BMI itself.

    Args:
        origin: the BMI object to proxy

    Example:
        To overwrite the `get_value` method of a BMI class, you can use the following

        >>> class MyBmi(BmiProxy):
        ...     def get_value(self, name: str, dest: np.ndarray) -> np.ndarray:
        ...         dest[:] = 1
        ...         return dest
        >>> bmi = MyBmi(BmiImplementation())
        >>> bmi.get_value("my_var", np.empty((2,3), dtype=np.float64))
        array([[1., 1., 1.], [1., 1., 1.]])

        All other methods are forwarded to the origin.

    """

    def __init__(self, origin: Bmi):
        self.origin = origin

    def finalize(self) -> None:
        return self.origin.finalize()

    def get_component_name(self) -> str:
        return self.origin.get_component_name()

    def get_current_time(self) -> float:
        return self.origin.get_current_time()

    def get_end_time(self) -> float:
        return self.origin.get_end_time()

    def get_grid_edge_count(self, grid: int) -> int:
        return self.origin.get_grid_edge_count(grid)

    def get_grid_edge_nodes(self, grid: int, edge_nodes: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_edge_nodes(grid, edge_nodes)

    def get_grid_face_count(self, grid: int) -> int:
        return self.origin.get_grid_face_count(grid)

    def get_grid_face_edges(self, grid: int, face_edges: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_face_edges(grid, face_edges)

    def get_grid_face_nodes(self, grid: int, face_nodes: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_face_nodes(grid, face_nodes)

    def get_grid_node_count(self, grid: int) -> int:
        return self.origin.get_grid_node_count(grid)

    def get_grid_nodes_per_face(
        self, grid: int, nodes_per_face: np.ndarray
    ) -> np.ndarray:
        return self.origin.get_grid_nodes_per_face(grid, nodes_per_face)

    def get_grid_origin(self, grid: int, shape: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_origin(grid, shape)

    def get_grid_rank(self, grid: int) -> int:
        return self.origin.get_grid_rank(grid)

    def get_grid_shape(self, grid: int, shape: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_shape(grid, shape)

    def get_grid_size(self, grid: int) -> int:
        return self.origin.get_grid_size(grid)

    def get_grid_spacing(self, grid: int, shape: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_spacing(grid, shape)

    def get_grid_type(self, grid: int) -> str:
        return self.origin.get_grid_type(grid)

    def get_grid_x(self, grid: int, x: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_x(grid, x)

    def get_grid_y(self, grid: int, y: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_y(grid, y)

    def get_grid_z(self, grid: int, z: np.ndarray) -> np.ndarray:
        return self.origin.get_grid_z(grid, z)

    def get_input_item_count(self) -> int:
        return self.origin.get_input_item_count()

    def get_input_var_names(self) -> tuple[str, ...]:  # type: ignore[override]
        return self.origin.get_input_var_names()

    def get_output_item_count(self) -> int:
        return self.origin.get_output_item_count()

    def get_output_var_names(self) -> tuple[str, ...]:  # type: ignore[override]
        return self.origin.get_output_var_names()

    def get_start_time(self) -> float:
        return self.origin.get_start_time()

    def get_time_step(self) -> float:
        return self.origin.get_time_step()

    def get_time_units(self) -> str:
        return self.origin.get_time_units()

    def get_value(self, name: str, dest: np.ndarray) -> np.ndarray:
        return self.origin.get_value(name, dest)

    def get_value_at_indices(
        self, name: str, dest: np.ndarray, inds: np.ndarray
    ) -> np.ndarray:
        return self.origin.get_value_at_indices(name, dest, inds)

    def get_value_ptr(self, name: str) -> np.ndarray:
        return self.origin.get_value_ptr(name)

    def get_var_itemsize(self, name: str) -> int:
        return self.origin.get_var_itemsize(name)

    def get_var_grid(self, name: str) -> int:
        return self.origin.get_var_grid(name)

    def get_var_location(self, name: str) -> str:
        return self.origin.get_var_location(name)

    def get_var_nbytes(self, name: str) -> int:
        return self.origin.get_var_nbytes(name)

    def get_var_type(self, name: str) -> str:
        return self.origin.get_var_type(name)

    def get_var_units(self, name: str) -> str:
        return self.origin.get_var_units(name)

    def initialize(self, filename: str) -> None:
        return self.origin.initialize(filename)

    def set_value(self, name: str, src: np.ndarray) -> None:
        return self.origin.set_value(name, src)

    def set_value_at_indices(
        self, name: str, inds: np.ndarray, src: np.ndarray
    ) -> None:
        return self.origin.set_value_at_indices(name, inds, src)

    def update(self) -> None:
        return self.origin.update()

    def update_until(self, time: float) -> None:
        return self.origin.update_until(time)
