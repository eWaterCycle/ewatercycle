# -*- coding: utf-8 -*-
import os
import subprocess
from abc import abstractmethod, ABC
from typing import Type, Dict


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
        if os.path.exists(target):
            raise Exception('Target directory already exists, will not overwrite')
        subprocess.check_call(['svn', 'export', self.source, target])


class SymlinkCopier(AbstractCopier):
    """Creates symlink from source to target
    """
    def save(self, target):
        os.symlink(self.source, target)


DATAFILES_FORMATS: Dict[str, Type[AbstractCopier]] = {
    'svn': SubversionCopier,
    'symlink': SymlinkCopier,
}
