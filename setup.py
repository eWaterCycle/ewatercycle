#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

version = {}
with open("ewatercycle/parametersetdb/version.py") as fp:
    exec(fp.read(), version)

setup(
    name='ewatercycle-parametersetdb',
    version=version['__version__'],
    description="Python utilities to gather input files for running a hydrology model",
    long_description=readme + '\n\n',
    author="Stefan Verhoeven",
    author_email='s.verhoeven@esciencecenter.nl',
    url='https://github.com/eWaterCycle/ewatercycle_parametersetdb',
    install_requires=['ruamel.yaml'],
    packages=['ewatercycle.parametersetdb'],
    include_package_data=True,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='ewatercycle',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    test_suite='tests',
    setup_requires=[
        # dependency for `python setup.py test`
        'pytest-runner',
        # dependencies for `python setup.py build_sphinx`
        'sphinx',
        'recommonmark',
        'sphinx_rtd_theme',
    ],
    tests_require=[
        'pytest',
        'pytest-cov',
        'pycodestyle',
    ],
    extras_require={
        'dev':  ['prospector[with_pyroma]', 'yapf', 'isort'],
    }
)
