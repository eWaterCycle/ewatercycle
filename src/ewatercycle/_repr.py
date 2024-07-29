"""__repr__ and friends helper."""

# Code copied from
# https://github.com/pydantic/pydantic/blob/3b3f400991ea2958c7492e4cdbfeb3d85dd48969/pydantic/_internal/_repr.py
import typing
from typing import Any

ReprArgs = typing.Iterable[tuple[str | None, Any]]
RichReprResult = typing.Iterable[
    Any | tuple[Any] | tuple[str, Any] | tuple[str, Any, Any]
]


class Representation:
    # Mixin to provide `__str__`, `__repr__`, and `__pretty__`
    # and `__rich_repr__` methods.
    # `__pretty__` is used by [devtools](https://python-devtools.helpmanual.io/).
    # `__rich_repr__` is used by [rich](https://rich.readthedocs.io/en/stable/pretty.html).
    # (this is not a docstring to avoid adding a docstring
    # to classes which inherit from Representation)

    def __repr_args__(self) -> ReprArgs:
        """Reusable helper for __repr__ and __pretty__.

        Can either return:
        * name - value pairs, for example
            `[('foo_name', 'foo'), ('bar_name', ['b', 'a', 'r'])]`
        * or, just values, for example
             `[(None, 'foo'), (None, ['b', 'a', 'r'])]`
        """
        attrs_names = self.__dict__.keys()
        attrs = ((s, getattr(self, s)) for s in attrs_names)
        return [(a, v) for a, v in attrs if v is not None]

    def __repr_name__(self) -> str:
        """Name of the instance's class, used in __repr__."""
        return self.__class__.__name__

    def __repr_str__(self, join_str: str) -> str:
        return join_str.join(
            repr(v) if a is None else f"{a}={v!r}" for a, v in self.__repr_args__()
        )

    def __pretty__(
        self, fmt: typing.Callable[[Any], Any], **kwargs: Any
    ) -> typing.Generator[Any, None, None]:
        """Formatter for devtools.

        Used by devtools (https://python-devtools.helpmanual.io/) to
        provide a human-readable representations of objects.
        """
        yield self.__repr_name__() + "("
        yield 1
        for name, value in self.__repr_args__():
            if name is not None:
                yield name + "="
            yield fmt(value)
            yield ","
            yield 0
        yield -1
        yield ")"

    def __str__(self) -> str:
        """The default implementation of __str__ just calls __repr."""
        return self.__repr_str__(" ")

    def __repr__(self) -> str:
        """The default implementation of __repr__ just calls __str__."""
        return f'{self.__repr_name__()}({self.__repr_str__(", ")})'

    def __rich_repr__(self) -> RichReprResult:
        """Get fields for Rich library."""
        for name, field_repr in self.__repr_args__():
            if name is None:
                yield field_repr
            else:
                yield name, field_repr

    # TODO add ipython rich display
    # see https://ipython.readthedocs.io/en/stable/config/integrating.html#rich-display
