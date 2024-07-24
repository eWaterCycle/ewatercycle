from ewatercycle.esmvaltool.missing import ESMValToolNotFoundError


def test_ESMValToolNotFoundError():
    err = ESMValToolNotFoundError()
    assert "conda-lock install" in str(err)
