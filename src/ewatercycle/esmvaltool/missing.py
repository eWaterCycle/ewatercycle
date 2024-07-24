"""Missing esmvaltool handler."""

import logging
from textwrap import dedent

logger = logging.getLogger(__name__)


def no_esmvaltool_found(e: ImportError):
    """Handle missing ESMValTool or ESMValCore packages.
    
    Args:
        e: ImportError that was raised when trying to import ESMValTool or ESMValCore.

    Raises:
        ImportError: With a message explaining how to install ESMValTool and ESMValCore.        
    """
    msg = dedent(
        """\
        ESMValTool or ESMValCore packages have not been found.

        Likely because ewatercycle dependencies are not installed in a conda environment.

        Please install ewatercycle with:

        ```shell
        wget https://raw.githubusercontent.com/eWaterCycle/ewatercycle/main/conda-lock.yml
        conda install mamba conda-lock -n base -c conda-forge -y
        conda-lock install --no-dev -n ewatercycle
        conda activate ewatercycle
        pip install ewatercycle
        ```
        """
    )
    raise ImportError(msg) from e
