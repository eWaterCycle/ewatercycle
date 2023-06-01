from logging import getLogger
from pathlib import Path
from shutil import unpack_archive
from typing import Optional, Set

import fsspec
from pydantic import BaseModel, HttpUrl

from ewatercycle.util import to_absolute_path

logger = getLogger(__name__)


class GitHubDownloader(BaseModel):
    org: str
    repo: str
    branch: Optional[str] = None
    path: str = ""

    """URL of directory in GitHub repository.

    Examples:

        * https://github.com/ec-jrc/lisflood-usecases/tree/master/LF_lat_lon_UseCase

    """

    def __call__(self, directory: Path):
        directory.mkdir(exist_ok=True, parents=True)
        fs = fsspec.filesystem("github", org=self.org, repo=self.repo, sha=self.branch)
        fs.get(fs.ls(self.path), directory.as_posix(), recursive=True)


class ZenodoDownloader(BaseModel):
    doi: str

    def __call__(self, directory: Path):
        # extract record id from doi
        # 10.5281/zenodo.7949784
        record_id = self.doi.split(".")[-1]
        # TODO Zenodo entry can have multiple files,
        # how to select the correct one? Pick first
        # TODO construct download url
        # url = 'https://zenodo.org/record/7949784/files/trixi-framework/Trixi.jl-v0.5.24.zip?download=1'
        # ArchiveDownloader(url=url)(directory)  # pyright: ignore


class ArchiveDownloader(BaseModel):
    """Download and unpack a parameter set from an archive file."""

    url: HttpUrl

    def __call__(self, directory: Path):
        with fsspec.open(self.url, "rb") as file:
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
    :py:attr:`~directory`."""
    doi: str = "N/A"
    """Persistent identifier of parameter set. For a example a DOI
    for a Zenodo record."""
    target_model: str = "generic"
    """Name of model that parameter set can work with."""
    supported_model_versions: Set[str] = set()
    """Set of model versions that are
    supported by this parameter set. If not set then parameter set will be
    supported by all versions of model"""
    downloader: GitHubDownloader | ZenodoDownloader | ArchiveDownloader | None = None

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

    def download(self, download_dir: Path, force: bool = False) -> None:
        self.make_absolute(download_dir)  # makes self.directory & self.config absolute
        if self.config.exists() and not force:
            logger.info(
                f"Directory {self.directory} for parameter set {self.name}"
                f" already exists and download is not forced, skipping download."
            )
            return None
        if self.downloader is None:
            raise ValueError(
                f"Cannot download parameter set {self.name} because no downloader is defined"
            )
        logger.info(
            f"Downloading example parameter set {self.name} to {self.directory}..."
        )
        self.downloader(self.directory)
        logger.info("Download complete.")
        return None

    @classmethod
    def from_github(cls, org: str, repo: str, branch: str, path: str, **kwargs):
        """Create a parameter set from a GitHub repository.
        Args:
            repo: URL of directory in GitHub repository.
            **kwargs: See :py:class:`ParameterSet` for other arguments.
        """
        kwargs.pop("downloader", None)
        downloader = GitHubDownloader(
            org=org,
            repo=repo,
            branch=branch,
            path=path,
        )  # pyright: ignore
        return ParameterSet(downloader=downloader, **kwargs)

    @classmethod
    def from_zenodo(cls, doi: str, **kwargs):
        kwargs.pop("downloader", None)
        downloader = ZenodoDownloader(doi=doi)
        return ParameterSet(doi=doi, downloader=downloader, **kwargs)

    @classmethod
    def from_archive_url(cls, url: str, **kwargs):
        kwargs.pop("downloader", None)
        downloader = ArchiveDownloader(url=url)  # pyright: ignore
        return ParameterSet(downloader=downloader, **kwargs)

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
                self.config, self.directory, must_be_in_parent=False
            )
        return self
