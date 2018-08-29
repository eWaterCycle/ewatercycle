# -*- coding: utf-8 -*-
from subprocess import check_call


class SubversionCopier:
    def __init__(self, source):
        self.source = source

    def save(self, target):
        check_call(['svn', 'export', self.source, target])
