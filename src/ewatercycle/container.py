"""Container utilities."""
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
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
    # TODO replace Any type with Bmi + BmiFromOrigin
    wrappers: Sequence[type[Any]] = (MemoizedBmi, OptionalDestBmi),
) -> OptionalDestBmi:
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
        wrappers: List of classes to wrap around the grcp4bmi object from container.
            Order is important. The first wrapper is the most inner wrapper.

    Raises:
        ValueError: When unknown container technology is requested.
        TimeoutError: When model inside container did not start quickly enough.

    Returns:
        When default wrappers are used then returns the
        :py:class:`Bmi object
        which wraps the container <grpc4bmi.bmi_grpc_client.BmiClient>`,
        has :py:class:`memoization <grpc4bmi.bmi_memoized.MemoizedBmi>` and
        has :py:class:`optional dest arguments <grpc4bmi.bmi_optionaldest.OptionalDestBmi>`.
        When no wrappers are used then returns the :py:class:`Bmi object
        which wraps the container <grpc4bmi.bmi_grpc_client.BmiClient>`.

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

    for wrapper in wrappers:
        bmi = wrapper(bmi)
    return bmi


def start_apptainer_container(
    work_dir: Union[str, Path],
    image: str,
    docker_image: str,
    input_dirs: Optional[Iterable[str]] = None,
    timeout: Optional[int] = None,
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
            input_dirs=tuple() if input_dirs is None else input_dirs,
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

    def get_input_var_names(self) -> Tuple[str, ...]:
        return self.origin.get_input_var_names()

    def get_output_item_count(self) -> int:
        return self.origin.get_output_item_count()

    def get_output_var_names(self) -> Tuple[str, ...]:
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
