"""Missing esmvaltool handler."""

import logging
from textwrap import dedent

logger = logging.getLogger(__name__)


class ESMValToolNotFoundError(ImportError):
    """Exception raised when ESMValTool or ESMValCore packages are not found."""

    def __init__(self):
        """Initialize the exception."""
        msg = dedent(
            """\
            ESMValTool or ESMValCore packages have not been found.

            Likely because ewatercycle dependencies are not installed
            in a conda environment.

            Please install ewatercycle with:

            ```shell
            curl -o conda-lock.yml https://raw.githubusercontent.com/eWaterCycle/ewatercycle/main/conda-lock.yml
            conda install mamba conda-lock -n base -c conda-forge -y
            conda-lock install --no-dev -n ewatercycle
            conda activate ewatercycle
            pip install ewatercycle
            ```
            """
        )
        super().__init__(msg)
