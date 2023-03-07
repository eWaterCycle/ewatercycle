"""Fake BMI models."""
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
