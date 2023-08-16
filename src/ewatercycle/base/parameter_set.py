import shutil
from io import BytesIO
from logging import getLogger
from pathlib import Path
from shutil import unpack_archive
from tempfile import TemporaryDirectory
from typing import Optional, Set
from urllib.request import urlopen
from zipfile import ZipFile

import fsspec
from pydantic import BaseModel, ConfigDict, HttpUrl

from ewatercycle.util import to_absolute_path

logger = getLogger(__name__)


def download_github_repo(
    org: str,
    repo: str,
    branch: str,
    download_dir: Path,
    subfolder: Optional[str] = None,
) -> None:
    """Download a Github repository .zip file, and extract (a subfolder) to a directory.

    Args:
        org: Github organization (e.g., "eWaterCycle")
        repo: Repository name (e.g, "ewatercycle")
        branch: Branch name (e.g., "main")
        download_dir: Path towards the directory where the data should be downloaded to.
        subfolder (optional): Subfolder within the github repo to extract.
            E.g. "src/ewatercycle/base".

    Raises:
        ConnectionError: If the HTTP return code is not 200.
    """
    zip_url = f"https://github.com/{org}/{repo}/archive/refs/heads/{branch}.zip"

    https_response = urlopen(zip_url)
    if https_response.status != 200:
        raise ConnectionError(
            f"HTTP error {https_response.status}\n"
            f"Attempted to connect to URL: {zip_url}"
        )

    with ZipFile(BytesIO(https_response.read())) as zipfile:
        main_folder = f"{repo}-{branch}"
        fpath = f"{main_folder}/{subfolder}" if subfolder is not None else main_folder
        fnames = [file for file in zipfile.namelist() if file.startswith(fpath)]
        for file in fnames:
            zipfile.extract(file, path=download_dir)


class GitHubDownloader(BaseModel):
    """Download and extract a Github repository.

    Examples:

        * https://github.com/ec-jrc/lisflood-usecases/tree/master/LF_lat_lon_UseCase

    """

    org: str
    "Github organization (e.g., 'eWaterCycle')"
    repo: str
    "Repository name (e.g, 'ewatercycle')"
    branch: str
    "Branch name (e.g., 'main')"
    subfolder: Optional[str] = None
    "Subfolder within the github repo to extract. E.g. 'src/ewatercycle/base'."

    def __call__(self, directory: Path):
        with TemporaryDirectory() as tmpdir_name:
            tmpdir = Path(tmpdir_name)
            download_github_repo(
                org=self.org,
                repo=self.repo,
                branch=self.branch,
                download_dir=tmpdir,
                subfolder=self.subfolder,
            )
            target_path = tmpdir / f"{self.repo}-{self.branch}"
            if self.subfolder is not None:
                target_path = target_path / self.subfolder

            shutil.copytree(
                src=target_path,
                dst=directory,
                dirs_exist_ok=True,
            )


class ZenodoDownloader(BaseModel):
    doi: str

    def __call__(self, directory: Path):
        raise NotImplementedError
        # extract record id from doi
        # 10.5281/zenodo.7949784
        # record_id = self.doi.split(".")[-1]
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
    """Container object for parameter set options.

    Is directory containing data that does not change over time.
    Should be passed to a models constructor like
    :py:class:`~ewatercycle.base.model.AbstractModel`.

    Example:

        >>> from ewatercycle.base import ParameterSet
        >>> parameter_set = ParameterSet(name='test', directory='test_dir', config='test_dir/config.yaml')
        >>> from ewatercycle.models import Wflow
        >>> model = Wflow(parameter_set=parameter_set)
    """

    name: str = ""
    """Name of parameter set"""
    directory: Path
    """Location on disk where files of parameter set are stored.

    If Path is relative then relative to CFG.parameterset_dir.
    """
    config: Path
    """Model configuration file which uses files from :py:attr:`~directory`.

    If Path is relative then relative to :py:attr:`~directory`.
    """
    doi: str = "N/A"
    """Persistent identifier of parameter set.

    For a example a DOI for a Zenodo record.
    """
    target_model: str = "generic"
    """Name of model that parameter set can work with."""
    supported_model_versions: Set[str] = set()
    """Set of model versions that are compatible with this parameter set.

    If not set then parameter set compability check silently passes."""
    downloader: GitHubDownloader | ZenodoDownloader | ArchiveDownloader | None = None
    """Method to download parameter set from somewhere."""
    model_config = ConfigDict(extra="forbid")

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
        """Download parameter set to directory.

        Args:
            download_dir: Directory where parameter set should be downloaded to.
            force: If True then download even if directory already exists.

        Raises:
            ValueError: If no downloader is defined.
        """
        self.make_absolute(download_dir)  # makes self.directory & self.config absolute
        if self.config.exists() and not force:
            logger.info(
                f"Directory {self.directory} for parameter set {self.name}"
                f" already exists and download is not forced, skipping download."
            )
            return None
        if self.downloader is None:
            raise ValueError(
                f"Cannot download parameter set {self.name} "
                "because no downloader is defined."
            )
        logger.info(
            f"Downloading example parameter set {self.name} to {self.directory}..."
        )
        self.downloader(self.directory)
        logger.info("Download complete.")
        return None

    @classmethod
    def from_github(
        cls, org: str, repo: str, branch: str, subfolder: Optional[str] = None, **kwargs
    ):
        """Create a parameter set from a GitHub repository.

        Args:
            org: GitHub organization (e.g., 'UU-Hydro')
            repo: Repository name (e.g, 'PCR-GLOBWB_input_example')
            branch: Branch name (e.g., 'master')
            subfolder: Subfolder within the github repo to extract. E.g.
                'pcrglobwb_rhinemeuse_30min'.
                If not given then downloads the entire repository.
            **kwargs: See :py:class:`ParameterSet` for other arguments.

        The example Github arguments would download all files from
        https://github.com/UU-Hydro/PCR-GLOBWB_input_example/tree/master/RhineMeuse30min
        """
        kwargs.pop("downloader", None)
        downloader = GitHubDownloader(
            org=org,
            repo=repo,
            branch=branch,
            subfolder=subfolder,
        )  # pyright: ignore
        return ParameterSet(downloader=downloader, **kwargs)

    @classmethod
    def from_zenodo(cls, doi: str, **kwargs) -> "ParameterSet":
        """Download a parameter set from Zenodo.

        Args:
            doi: DOI of Zenodo record. E.g. '10.5281/zenodo.1045339'.
            **kwargs: See :py:class:`ParameterSet` for other arguments.
        """
        kwargs.pop("downloader", None)
        downloader = ZenodoDownloader(doi=doi)
        return ParameterSet(doi=doi, downloader=downloader, **kwargs)

    @classmethod
    def from_archive_url(cls, url: str, **kwargs) -> "ParameterSet":
        """Download a parameter set from an archive file on the Internet.

        Args:
            url: Link to archive file.
            **kwargs: See :py:class:`ParameterSet` for other arguments.

        Example:

            >>> from ewatercycle.base import ParameterSet
            >>> url = ''
            >>> parameter_set = ParameterSet.from_archive_url(url)
        """
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
