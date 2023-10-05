"""Functions for loading/editting/saving lisflood config files."""

from xml.etree import ElementTree as ET


class XmlConfig:
    """Config container where config is read/saved in xml format."""

    def __init__(self, source):
        """Config container where config is read/saved in xml format.
        Args:
            source: file to read from
        """
        self.tree = ET.parse(source)
        self.config = self.tree.getroot()  # mypy complains with ET.Element
        """XML element used to make changes to the config"""

    def save(self, target):
        """Save xml to file.
        Args:
            target: file to save to
        """
        self.tree.write(target)
