import pytest

from ewatercycle.base.forcing import DefaultForcing
from ewatercycle.forcing import sources as forcing_sources
from ewatercycle.models import sources as model_sources


@pytest.mark.parametrize(
    "forcing_name",
    ["LumpedMakkinkForcing", "DistributedUserForcing", "GenericDistributedForcing"],
)
def test_forcings(forcing_name):
    assert forcing_name in forcing_sources.keys()


def test_forcings_getitem():
    assert issubclass(forcing_sources.LumpedMakkinkForcing, DefaultForcing)


def test_forcings_square_brackets():
    assert issubclass(forcing_sources["LumpedMakkinkForcing"], DefaultForcing)


def test_forcings_len():
    assert len(forcing_sources) >= 6


def test_rich_repr():
    rrepr = forcing_sources.__rich__()
    assert len(rrepr.split("\n")) - 2 == len(forcing_sources)


def test_models():
    """Can't depend on models being installed, i.e. available."""
    model_sources.keys()
