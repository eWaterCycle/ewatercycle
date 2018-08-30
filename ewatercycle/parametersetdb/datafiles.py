# -*- coding: utf-8 -*-
import subprocess
from abc import abstractmethod, ABC


class AbstractCopier(ABC):
    def __init__(self, source: str):
        """

        Args:
            source: Source url of datafiles
        """
        self.source = source

    @abstractmethod
    def save(self, target: str):
        """Saves datafiles to target directory

        Args:
            target: Directory where to save the datafiles

        Returns:

        """
        pass


class SubversionCopier(AbstractCopier):
    """Uses subversion export to copy files from source to target
    """
    def save(self, target):
        subprocess.check_call(['svn', 'export', self.source, target])


DATAFILES_FORMATS = {
    'svn': SubversionCopier
}
