import abc
import datetime
from pathlib import Path
from typing import Any, Type

import bmipy
import pydantic
import yaml

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.config import CFG
from ewatercycle.container import start_container
from ewatercycle.util import to_absolute_path


class BaseModel(pydantic.BaseModel, abc.ABC):
    """Base functionality for eWaterCycle models.

    Can't be instantiated directly because children need to specify how to
    make their BMI instance.
    """

    forcing: DefaultForcing
    parameter_set: ParameterSet
    parameters: dict[str, Any]

    @abc.abstractmethod
    def _make_bmi_instance(self):
        """Attach a BMI instance to self.bmi"""

    def setup(self, *, cfg_dir: str | None = None, **kwargs) -> tuple[str, str]:
        """Instantiate Bmi model and return config file and work dir.

        Args:
            cfg_dir: Optionally specify path to use as config dir. Will be
                created if it doesn't exist yet. Behaviour follows PyMT
                documentation (see note below).
            **kwargs: Use :py:meth:`parameters` to see the
                configurable options for this model and their current values

        Returns: Path to config file and work dir

        Note:
            Modelled after pymt:
            https://pymt.readthedocs.io/en/latest/usage.html#model-setup. Only
            difference is that we don't create a temporary directory, but rather
            a time-stamped folder inside ewatercycle.CFG['output_dir'].

        """
        self.cfg_dir: Path = self._make_cfg_dir(cfg_dir)
        self.cfg_file = self._make_cfg_file(**kwargs)
        self.bmi = self._make_bmi_instance()

        return str(self.cfg_file), str(self.cfg_dir)

    def _make_cfg_dir(self, cfg_dir):
        if cfg_dir is not None:
            cfg_dir = to_absolute_path(cfg_dir)
        else:
            tz = datetime.timezone.utc
            timestamp = datetime.datetime.now(tz).strftime("%Y%m%d_%H%M%S")
            cfg_dir = to_absolute_path(
                f"ewatercycle_{timestamp}", parent=CFG.output_dir
            )

        cfg_dir.mkdir(parents=True, exist_ok=True)

        return cfg_dir

    def _make_cfg_file(self, **kwargs):
        cfg_file = self.cfg_dir / "config.yaml"
        self.parameters.update(**kwargs)
        with open(cfg_file, "w") as file:
            yaml.dump({k: v for k, v in self.parameters}, file)

        return cfg_file


class LocalModel(BaseModel):
    """eWaterCycle model running in a local Python environment.

    Mostly intended for development purposes.
    """

    bmi_class: Type[bmipy.Bmi]

    def _make_bmi_instance(self):
        return self.bmi_class()


class ContainerizedModel(BaseModel):
    """eWaterCycle model running inside a container.

    This is the recommended method for sharing eWaterCycle models.
    """

    bmi_image: str = "ghcr.io/ewatercycle/leakybucket-grpc4bmi:latest"

    def _make_bmi_instance(self) -> bmipy.Bmi:
        self.additional_input_dirs = []
        if self.parameter_set:
            self.additional_input_dirs.append(str(self.parameter_set.directory))
        if self.forcing:
            self.additional_input_dirs.append(str(self.forcing.directory))

        grpc4bmi = start_container(
            image_engine=self.bmi_image,  # TODO: find way to infer image name based on CFG['container_engine']
            work_dir=self.cfg_dir,
            input_dirs=self.additional_input_dirs,
            timeout=300,
        )
        return grpc4bmi
