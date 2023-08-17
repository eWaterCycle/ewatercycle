from bmipy import Bmi
import numpy as np
from typing import Tuple


class BmiEverythingOptional(Bmi):
    def initialize(self, config_file: str) -> None:
        raise NotImplementedError()

    def update(self) -> None:
        raise NotImplementedError()

    def update_until(self, time: float) -> None:
        raise NotImplementedError()

    def finalize(self) -> None:
        raise NotImplementedError()

    def get_component_name(self) -> str:
        raise NotImplementedError()

    def get_input_item_count(self) -> int:
        raise NotImplementedError()

    def get_output_item_count(self) -> int:
        raise NotImplementedError()

    def get_input_var_names(self) -> Tuple[str]:
        raise NotImplementedError()

    def get_output_var_names(self) -> Tuple[str]:
        raise NotImplementedError()

    def get_var_grid(self, name: str) -> int:
        raise NotImplementedError()

    def get_var_type(self, name: str) -> str:
        raise NotImplementedError()

    def get_var_units(self, name: str) -> str:
        raise NotImplementedError()

    def get_var_itemsize(self, name: str) -> int:
        raise NotImplementedError()

    def get_var_nbytes(self, name: str) -> int:
        raise NotImplementedError()

    def get_var_location(self, name: str) -> str:
        raise NotImplementedError()

    def get_current_time(self) -> float:
        raise NotImplementedError()

    def get_start_time(self) -> float:
        raise NotImplementedError()

    def get_end_time(self) -> float:
        raise NotImplementedError()

    def get_time_units(self) -> str:
        raise NotImplementedError()

    def get_time_step(self) -> float:
        raise NotImplementedError()

    def get_value(self, name: str, dest: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_value_ptr(self, name: str) -> np.ndarray:
        raise NotImplementedError()

    def get_value_at_indices(
        self, name: str, dest: np.ndarray, inds: np.ndarray
    ) -> np.ndarray:
        raise NotImplementedError()

    def set_value(self, name: str, values: np.ndarray) -> None:
        raise NotImplementedError()

    def set_value_at_indices(
        self, name: str, inds: np.ndarray, src: np.ndarray
    ) -> None:
        raise NotImplementedError()

    def get_grid_rank(self, grid: int) -> int:
        raise NotImplementedError()

    def get_grid_size(self, grid: int) -> int:
        raise NotImplementedError()

    def get_grid_type(self, grid: int) -> str:
        raise NotImplementedError()

    def get_grid_shape(self, grid: int, shape: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_spacing(self, grid: int, spacing: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_origin(self, grid: int, origin: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_x(self, grid: int, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_y(self, grid: int, y: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_z(self, grid: int, z: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_node_count(self, grid: int) -> int:
        raise NotImplementedError()

    def get_grid_edge_count(self, grid: int) -> int:
        raise NotImplementedError()

    def get_grid_face_count(self, grid: int) -> int:
        raise NotImplementedError()

    def get_grid_edge_nodes(self, grid: int, edge_nodes: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_face_edges(self, grid: int, face_edges: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_face_nodes(self, grid: int, face_nodes: np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def get_grid_nodes_per_face(
        self, grid: int, nodes_per_face: np.ndarray
    ) -> np.ndarray:
        raise NotImplementedError()
