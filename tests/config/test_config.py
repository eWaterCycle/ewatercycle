from collections.abc import MutableMapping
from pathlib import Path

import numpy as np
import pytest

from ewatercycle import CFG
from ewatercycle.config._config_object import Config
from ewatercycle.config._validated_config import InvalidConfigParameter
from ewatercycle.config._validators import (
    _listify_validator,
    validate_float,
    validate_int,
    validate_int_or_none,
    validate_path,
    validate_path_or_none,
    validate_string,
    validate_string_or_none,
)


def generate_validator_testcases(valid):
    # The code for this function was taken from matplotlib (v3.3) and modified
    # to fit the needs of ewatercycle. Matplotlib is licenced under the terms of
    # the the 'Python Software Foundation License'
    # (https://www.python.org/psf/license)

    validation_tests = (
        {
            "validator": _listify_validator(validate_float, n_items=2),
            "success": (
                (_, [1.5, 2.5])
                for _ in (
                    "1.5, 2.5",
                    [1.5, 2.5],
                    [1.5, 2.5],
                    (1.5, 2.5),
                    np.array((1.5, 2.5)),
                )
            ),
            "fail": ((_, ValueError) for _ in ("fail", ("a", 1), (1, 2, 3))),
        },
        {
            "validator": _listify_validator(validate_float, n_items=2),
            "success": (
                (_, [1.5, 2.5])
                for _ in (
                    "1.5, 2.5",
                    [1.5, 2.5],
                    [1.5, 2.5],
                    (1.5, 2.5),
                    np.array((1.5, 2.5)),
                )
            ),
            "fail": ((_, ValueError) for _ in ("fail", ("a", 1), (1, 2, 3))),
        },
        {
            "validator": _listify_validator(validate_int, n_items=2),
            "success": (
                (_, [1, 2])
                for _ in ("1, 2", [1.5, 2.5], [1, 2], (1, 2), np.array((1, 2)))
            ),
            "fail": ((_, ValueError) for _ in ("fail", ("a", 1), (1, 2, 3))),
        },
        {
            "validator": validate_int_or_none,
            "success": ((None, None),),
            "fail": (),
        },
        {
            "validator": validate_path,
            "success": (
                ("a/b/c", Path.cwd() / "a" / "b" / "c"),
                ("/a/b/c/", Path("/", "a", "b", "c")),
                ("~/", Path.home()),
            ),
            "fail": (
                (None, ValueError),
                (123, ValueError),
                (False, ValueError),
                ([], ValueError),
            ),
        },
        {
            "validator": validate_path_or_none,
            "success": ((None, None),),
            "fail": (),
        },
        {
            "validator": _listify_validator(validate_string),
            "success": (
                ("", []),
                ("a,b", ["a", "b"]),
                ("abc", ["abc"]),
                ("abc, ", ["abc"]),
                ("abc, ,", ["abc"]),
                (["a", "b"], ["a", "b"]),
                (("a", "b"), ["a", "b"]),
                (iter(["a", "b"]), ["a", "b"]),
                (np.array(["a", "b"]), ["a", "b"]),
                ((1, 2), ["1", "2"]),
                (np.array([1, 2]), ["1", "2"]),
            ),
            "fail": (
                (set(), ValueError),
                (1, ValueError),
            ),
        },
        {
            "validator": validate_string_or_none,
            "success": ((None, None),),
            "fail": (),
        },
    )

    for validator_dict in validation_tests:
        validator = validator_dict["validator"]
        if valid:
            for arg, target in validator_dict["success"]:
                yield validator, arg, target
        else:
            for arg, error_type in validator_dict["fail"]:
                yield validator, arg, error_type


@pytest.mark.parametrize("validator, arg, target", generate_validator_testcases(True))
def test_validator_valid(validator, arg, target):
    """Test valid cases for the validators."""
    res = validator(arg)
    assert res == target


@pytest.mark.parametrize(
    "validator, arg, exception_type", generate_validator_testcases(False)
)
def test_validator_invalid(validator, arg, exception_type):
    """Test invalid cases for the validators."""
    with pytest.raises(exception_type):
        validator(arg)


def test_config_object():
    """Test that the config is of the right type."""
    assert isinstance(CFG, MutableMapping)

    del CFG["output_dir"]
    assert "output_dir" not in CFG

    CFG.reload()
    assert "output_dir" in CFG


def test_config_update():
    """Test whether `config.update` raises the correct exception."""
    config = Config({"output_dir": "directory"})
    fail_dict = {"output_dir": 123}

    with pytest.raises(InvalidConfigParameter):
        config.update(fail_dict)


def test_config_class():
    """Test that the validators turn strings into paths."""
    config = {
        "container_engine": "docker",
        "grdc_location": "path/to/grdc_location",
        "output_dir": "path/to/output_dir",
        "singularity_dir": "path/to/singularity_dir",
        "parameterset_dir": "path/to/parameter_sets",
        "parameter_sets": {},
    }

    cfg = Config(config)

    assert isinstance(cfg["container_engine"], str)
    assert isinstance(cfg["grdc_location"], Path)
    assert isinstance(cfg["output_dir"], Path)
    assert isinstance(cfg["singularity_dir"], Path)
    assert isinstance(cfg["parameterset_dir"], Path)
    assert isinstance(cfg["parameter_sets"], dict)
