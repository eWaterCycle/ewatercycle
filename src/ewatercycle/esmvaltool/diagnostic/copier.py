"""ESMValTool diagnostic script that copies the preprocessing output to the diagnostic output."""
import logging
import shutil
from pathlib import Path

from esmvaltool.diag_scripts.shared import (
    ProvenanceLogger,
    get_diagnostic_filename,
    run_diagnostic,
)

logger = logging.getLogger(Path(__file__).name)


def main(cfg):
    """Copy input data to the output directory.

    Args:
        cfg: Configuration dictionary.
    """
    input_data = cfg["input_data"]
    provenance = {
        "caption": "Forcings for generic hydrological model",
        "domains": ["global"],
        "authors": [
            "unmaintained",
        ],
        "projects": [
            "ewatercycle",
        ],
        "references": [
            "acknow_project",
        ],
    }
    for input_file in input_data.keys():
        input_path = Path(input_file)
        outfile = get_diagnostic_filename(input_path.stem, cfg, input_path.suffix[1:])
        logger.info("Copying %s to %s", input_file, outfile)
        shutil.copy(input_file, outfile)
        with ProvenanceLogger(cfg) as provenance_logger:
            provenance_logger.log(
                outfile,
                {
                    **provenance,
                    "ancestors": [input_file],
                },
            )


if __name__ == "__main__":
    with run_diagnostic() as config:
        main(config)
