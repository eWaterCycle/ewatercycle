"""Fake BMI models."""
from unittest.mock import Mock

import numpy as np
from bmipy import Bmi


class SomeException(Exception):
    pass


class FailingModel(Bmi):
    def __init__(self, exc=SomeException()):
        self.exc = exc

    def initialize(self, filename):
        raise self.exc

    def update(self):
        raise self.exc

    def update_until(self, time: float) -> None:
        raise self.exc

    def finalize(self):
        raise self.exc

    def get_component_name(self):
        raise self.exc

    def get_input_item_count(self) -> int:
        raise self.exc

    def get_output_item_count(self) -> int:
        raise self.exc

    def get_input_var_names(self):
        raise self.exc

    def get_output_var_names(self):
        raise self.exc

    def get_start_time(self):
        raise self.exc

    def get_current_time(self):
        raise self.exc

    def get_end_time(self):
        raise self.exc

    def get_time_step(self):
        raise self.exc

    def get_time_units(self):
        raise self.exc

    def get_var_type(self, name):
        raise self.exc

    def get_var_units(self, name):
        raise self.exc

    def get_var_itemsize(self, name):
        raise self.exc

    def get_var_nbytes(self, name):
        raise self.exc

    def get_var_grid(self, name):
        raise self.exc

    def get_value(self, name, dest):
        raise self.exc

    def get_value_ptr(self, name):
        raise self.exc

    def get_value_at_indices(self, name, dest, inds):
        raise self.exc

    def set_value(self, name, src):
        raise self.exc

    def set_value_at_indices(self, name, inds, src):
        raise self.exc

    def get_grid_shape(self, grid, shape):
        raise self.exc

    def get_grid_x(self, grid, x):
        raise self.exc

    def get_grid_y(self, grid, y):
        raise self.exc

    def get_grid_z(self, grid, z):
        raise self.exc

    def get_grid_spacing(self, grid, spacing):
        raise self.exc

    def get_grid_origin(self, grid, origin):
        raise self.exc

    def get_grid_rank(self, grid):
        raise self.exc

    def get_grid_size(self, grid):
        raise self.exc

    def get_grid_type(self, grid):
        raise self.exc

    def get_var_location(self, name: str) -> str:
        raise self.exc

    def get_grid_node_count(self, grid: int) -> int:
        raise self.exc

    def get_grid_edge_count(self, grid: int) -> int:
        raise self.exc

    def get_grid_face_count(self, grid: int) -> int:
        raise self.exc

    def get_grid_edge_nodes(self, grid: int, edge_nodes: np.ndarray) -> np.ndarray:
        raise self.exc

    def get_grid_face_nodes(self, grid: int, face_nodes: np.ndarray) -> np.ndarray:
        raise self.exc

    def get_grid_nodes_per_face(
        self, grid: int, nodes_per_face: np.ndarray
    ) -> np.ndarray:
        raise self.exc

    def get_grid_face_edges(self, grid: int, face_edges: np.ndarray) -> np.ndarray:
        raise self.exc


class NotImplementedModel(FailingModel):
    def __init__(self, exc=NotImplementedError()):
        super().__init__(exc=exc)


class WithMocksMixin:
    """Mock the bmi methods that return None and have no getter companion.

    Use `instance.mock.<method name>.assert_called_once_with()`
    to check if the method is called correctly.
    """

    def __init__(self):
        self.mock = Mock()

    def initialize(self, config_file: str) -> None:
        self.mock.initialize(config_file)

    def finalize(self):
        self.mock.finalize()


class WithDailyMixin:
    """Mock the bmi methods that deal wtih time.

    Behaves like a daily model which started since epoch.
    """

    def __init__(self) -> None:
        self.time = 0.0

    def update(self):
        self.time = self.time + self.get_time_step()

    def get_current_time(self):
        return self.time

    def get_start_time(self):
        return 0.0

    def get_end_time(self):
        return 100.0

    def get_time_step(self):
        return 1.0

    def get_time_units(self):
        return "days since 1970-01-01"


class DummyModelWith2DRectilinearGrid(
    WithMocksMixin, WithDailyMixin, NotImplementedModel
):
    def __init__(self):
        super().__init__()
        # not sure why extra call to init is needed,
        # but without the self.time is not initialized
        WithMocksMixin.__init__(self)
        WithDailyMixin.__init__(self)
        self.dtype = np.dtype("float32")
        self.value = np.array(
            [
                1.1,
                2.2,
                3.3,
                4.4,
                5.5,
                6.6,
                7.7,
                8.8,
                9.9,
                10.1,
                11.1,
                12.1,
            ],
            dtype=self.dtype,
        )

    def get_output_var_names(self) -> tuple[str]:
        return ("plate_surface__temperature",)

    def get_input_var_names(self):
        return ()

    def get_var_type(self, name):
        return str(self.dtype)

    def get_var_grid(self, name):
        return 0

    def get_var_units(self, name):
        return "K"

    def get_var_itemsize(self, name):
        return self.dtype.itemsize

    def get_var_nbytes(self, name):
        return self.dtype.itemsize * self.value.size

    def get_grid_type(self, grid):
        return "rectilinear"

    def get_grid_size(self, grid):
        return 12  # 4 longs * 3 lats

    def get_grid_rank(self, grid: int) -> int:
        return 2

    def get_grid_shape(self, grid: int, shape: np.ndarray) -> np.ndarray:
        np.copyto(src=[3, 4], dst=shape)
        return shape

    def get_value(self, name, dest):
        np.copyto(src=self.value, dst=dest)
        return dest

    def get_value_at_indices(self, name, dest, inds):
        np.copyto(src=self.value[inds], dst=dest)
        return dest

    def set_value(self, name, src):
        self.value[:] = src

    def set_value_at_indices(self, name, inds, src):
        self.value[inds] = src

    def get_grid_x(self, grid: int, x: np.ndarray) -> np.ndarray:
        np.copyto(src=[0.1, 0.2, 0.3, 0.4], dst=x)
        return x

    def get_grid_y(self, grid: int, y: np.ndarray) -> np.ndarray:
        np.copyto(src=[1.1, 1.2, 1.3], dst=y)
        return y
