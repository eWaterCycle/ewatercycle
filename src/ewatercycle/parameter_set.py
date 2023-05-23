from logging import getLogger
from pathlib import Path
from shutil import unpack_archive
from typing import Set
import fsspec

from gitdir.gitdir import download as github_download
from pydantic import BaseModel, HttpUrl

from ewatercycle.util import to_absolute_path
from ewatercycle.config import CFG

logger = getLogger(__name__)

class GitHubDownloader(BaseModel):
    repo: HttpUrl
    """URL of directory in GitHub repository. 

    Examples:

        * https://github.com/ec-jrc/lisflood-usecases/tree/master/LF_lat_lon_UseCase

    """

    def __call__(self, directory: Path):
        github_download(self.repo, False, str(directory))

class ZenodoDownloader(BaseModel):
    doi: str

    def __call__(self, directory: Path):
        # extract record id from doi 
        # 10.5281/zenodo.7949784
        record_id = self.doi.split('.')[-1]
        # TODO Zenodo entry can have multiple files, 
        # how to select the correct one? Pick first
        # TODO construct download url
        # url = 'https://zenodo.org/record/7949784/files/trixi-framework/Trixi.jl-v0.5.24.zip?download=1'
        ArchiveDownloader(url=url)(directory)  # pyright: ignore

class ArchiveDownloader(BaseModel):
    """Download and unpack a parameter set from an archive file.	"""	
    url: HttpUrl

    def __call__(self, directory: Path):
        with fsspec.open(self.url, 'rb') as file:
            unpack_archive(file, directory)

class ParameterSet(BaseModel):
    """Container object for parameter set options."""

    name: str = ""
    """Name of parameter set"""
    directory: Path
    """Location on disk where files of parameter set are stored.
    If Path is relative then relative to CFG.parameterset_dir."""
    config: Path
    """Model configuration file which uses files from
    :py:attr:`~directory`. If Path is relative then relative to
    CFG.parameterset_dir."""
    doi: str = "N/A"
    """Persistent identifier of parameter set. For a example a DOI
    for a Zenodo record."""
    target_model: str = "generic"
    """Name of model that parameter set can work with."""
    supported_model_versions: Set[str] = set()
    """Set of model versions that are
    supported by this parameter set. If not set then parameter set will be
    supported by all versions of model"""
    downloader: GitHubDownloader |  | None = None
    
    class Config:
        extra = "forbid"

    def __str__(self):
        """Nice formatting of parameter set."""
        return "\n".join(
            [
                "Parameter set",
                "-------------",
            ]
            + [f"{k}={v!s}" for k, v in self.__dict__.items()]
        )

    def download(self, force=False):
        self.make_absolute(CFG.parameterset_dir)
        if not self.config.exists() and not force:
            logger.info(
                f"Directory {self.directory} for parameter set {self.name}"
                f" already exists and download is not forced, skipping download."
            )
            return
        if self.downloader is None:
            raise ValueError(
                f"Cannot download parameter set {self.name} because no downloader is defined"
            )
        logger.info(
            f"Downloading example parameter set {self.name} to {self.directory}..."
        )
        self.downloader(self.directory)
        logger.info("Download complete.")


    @classmethod
    def from_github(cls, repo: str , **kwargs):
        """Create a parameter set from a GitHub repository.

        Args:
            repo: URL of directory in GitHub repository.
            **kwargs: See :py:class:`ParameterSet` for other arguments.
        """
        kwargs.pop('downloader')
        # TODO deal with missing directory
        downloader = GitHubDownloader(repo=repo)  # pyright: ignore
        return ParameterSet(downloader=downloader,
                            **kwargs)

    @classmethod
    def from_zenodo(cls, doi: str, **kwargs):
        kwargs.pop('doi')
        kwargs.pop('downloader')
        downloader = ZenodoDownloader(doi=doi)
        return ParameterSet(doi=doi,
                            downloader=downloader,
                            **kwargs)
    
    @classmethod
    def from_archive_url(cls, url: str, **kwargs):
        kwargs.pop('downloader')
        downloader = ArchiveDownloader(url=url)  # pyright: ignore
        return ParameterSet(downloader=downloader,
                            **kwargs)

    def make_absolute(self, parameterset_dir: Path) -> "ParameterSet":
        """Make self.directory and self.config absolute paths.

        Args:
            parameterset_dir: Directory to which relative paths should be made absolute.

        Returns:
            self
        """
        if not self.directory.is_absolute():
            self.directory = to_absolute_path(
                self.directory, parameterset_dir, must_be_in_parent=False
            )
        if not self.config.is_absolute():
            self.config = to_absolute_path(
                self.config, parameterset_dir, must_be_in_parent=False
            )
        return self

def add_to_config(parameter_set: ParameterSet):
    """Add a parameter set to the ewatercycle.CFG object."""
    logger.info(f"Adding parameterset {parameter_set.name} to ewatercycle.CFG... ")

    if not CFG.parameter_sets:
        CFG.parameter_sets = {}

    CFG.parameter_sets[self.name] = dict(
        directory=str(_abbreviate(parameter_set.directory)),
        config=str(_abbreviate(parameter_set.config)),
        doi=parameter_set.doi,
        target_model=parameter_set.target_model,
        supported_model_versions=parameter_set.supported_model_versions,
    )

def _abbreviate(path: Path):
    try:
        if CFG.parameterset_dir is None:
            raise ValueError(f"Can not abbreviate path without CFG.parameterset_dir")
        return path.relative_to(CFG.parameterset_dir)
    except ValueError:
        return path
