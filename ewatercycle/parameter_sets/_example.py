import subprocess
from logging import getLogger
from pathlib import Path
from urllib.request import urlopen

from ewatercycle import CFG
from .default import ParameterSet

logger = getLogger(__name__)


class ExampleParameterSet(ParameterSet):
    def __init__(
        self,
        config_url: str,
        datafiles_url: str,
        name,
        directory: str,
        config: str,
        doi="N/A",
        target_model="generic",
    ):
        super().__init__(name, directory, config, doi, target_model)
        self.config_url = config_url
        self.datafiles_url = datafiles_url

    def download(self):
        if self.directory.exists():
            raise ValueError("Directory already exists, will not overwrite")

        logger.info(
            f"Downloading example parameter set {self.name} to {self.directory}..."
        )

        subprocess.check_call(["svn", "export", self.datafiles_url, self.directory])
        # TODO replace subversion with alternative see https://stackoverflow.com/questions/33066582/how-to-download-a-folder-from-github/48948711
        with urlopen(self.config_url) as response:
            self.config.write_text(response.read().decode())

        logger.info("Download complete.")

    def to_config(self):
        logger.info(f"Adding parameterset {self.name} to ewatercycle.CFG... ")

        if not CFG["parameter_sets"]:
            CFG["parameter_sets"] = {}

        CFG["parameter_sets"][self.name] = dict(
            directory=str(_abbreviate(self.directory)),
            config=str(_abbreviate(self.config)),
            doi=self.doi,
            target_model=self.target_model,
        )


def _abbreviate(path: Path):
    try:
        return path.relative_to(CFG["parameterset_dir"])
    except ValueError:
        return path
