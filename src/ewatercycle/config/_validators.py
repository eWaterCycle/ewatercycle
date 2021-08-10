"""List of config validators."""

import warnings
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path


class ValidationError(ValueError):
    """Custom validation error."""


# The code for this function was taken from matplotlib (v3.3) and modified
# to fit the needs of eWaterCycle. Matplotlib is licenced under the terms of
# the the 'Python Software Foundation License'
# (https://www.python.org/psf/license)
def _make_type_validator(cls, *, allow_none=False):
    """Construct a type validator for `cls`.

    Return a validator that converts inputs to *cls* or raises (and
    possibly allows ``None`` as well).
    """

    def validator(inp):
        looks_like_none = isinstance(inp, str) and (inp.lower() == "none")
        if allow_none and (inp is None or looks_like_none):
            return None
        try:
            return cls(inp)
        except ValueError as err:
            if isinstance(cls, type):
                raise ValidationError(
                    f"Could not convert {repr(inp)} to {cls.__name__}"
                ) from err
            raise

    validator.__name__ = f"validate_{cls.__name__}"
    if allow_none:
        validator.__name__ += "_or_None"
    validator.__qualname__ = (
        validator.__qualname__.rsplit(".", 1)[0] + "." + validator.__name__
    )
    return validator


# The code for this function was taken from matplotlib (v3.3) and modified
# to fit the needs of eWaterCycle. Matplotlib is licenced under the terms of
# the the 'Python Software Foundation License'
# (https://www.python.org/psf/license)
@lru_cache()
def _listify_validator(
    scalar_validator, allow_stringlist=False, *, n_items=None, docstring=None
):
    """Apply the validator to a list."""

    def func(inp):
        if isinstance(inp, str):
            try:
                inp = [
                    scalar_validator(val.strip())
                    for val in inp.split(",")
                    if val.strip()
                ]
            except Exception:
                if allow_stringlist:
                    # Sometimes, a list of colors might be a single string
                    # of single-letter colornames. So give that a shot.
                    inp = [
                        scalar_validator(val.strip())
                        for val in inp
                        if val.strip()
                    ]
                else:
                    raise
        # Allow any ordered sequence type -- generators, np.ndarray, pd.Series
        # -- but not sets, whose iteration order is non-deterministic.
        elif isinstance(inp, Iterable) and not isinstance(
            inp, (set, frozenset)
        ):
            # The condition on this list comprehension will preserve the
            # behavior of filtering out any empty strings (behavior was
            # from the original validate_stringlist()), while allowing
            # any non-string/text scalar values such as numbers and arrays.
            inp = [
                scalar_validator(val)
                for val in inp
                if not isinstance(val, str) or val
            ]
        else:
            raise ValidationError(
                f"Expected str or other non-set iterable, but got {inp}"
            )
        if n_items is not None and len(inp) != n_items:
            raise ValidationError(
                f"Expected {n_items} values, "
                f"but there are {len(inp)} values in {inp}"
            )
        return inp

    try:
        func.__name__ = "{}list".format(scalar_validator.__name__)
    except AttributeError:  # class instance.
        func.__name__ = "{}List".format(type(scalar_validator).__name__)
    func.__qualname__ = (
        func.__qualname__.rsplit(".", 1)[0] + "." + func.__name__
    )
    if docstring is not None:
        docstring = scalar_validator.__doc__
    func.__doc__ = docstring
    return func


def validate_path(value, allow_none=False):
    """Return a `Path` object."""
    if (value is None) and allow_none:
        return value
    try:
        path = Path(value).expanduser().absolute()
    except TypeError as err:
        raise ValidationError(f"Expected a path, but got {value}") from err
    else:
        return path


validate_string = _make_type_validator(str)
validate_string_or_none = _make_type_validator(str, allow_none=True)
validate_stringlist = _listify_validator(
    validate_string, docstring="Return a list of strings."
)
validate_int = _make_type_validator(int)
validate_int_or_none = _make_type_validator(int, allow_none=True)
validate_float = _make_type_validator(float)
validate_floatlist = _listify_validator(
    validate_float, docstring="Return a list of floats."
)

validate_path_or_none = _make_type_validator(validate_path, allow_none=True)

validate_pathlist = _listify_validator(
    validate_path, docstring="Return a list of paths."
)

validate_dict_parameterset = _make_type_validator(dict, allow_none=True)

_validators = {
    "grdc_location": validate_path_or_none,
    "container_engine": validate_string_or_none,
    "singularity_dir": validate_path_or_none,
    "output_dir": validate_path_or_none,
    "parameterset_dir": validate_path_or_none,
    "parameter_sets": validate_dict_parameterset,
    "ewatercycle_config": validate_path_or_none,
}
