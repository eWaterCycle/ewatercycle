#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

version = {}
with open("ewatercycle/version.py") as fp:
    exec(fp.read(), version)

setup(
    name='ewatercycle',
    version=version['__version__'],
    description="A Python package for running and validating a hydrology model",
    long_description=readme + '\n\n',
    author="Stefan Verhoeven",
    author_email='s.verhoeven@esciencecenter.nl',
    url='https://github.com/eWaterCycle/ewatercycle',
    install_requires=[
        'basic_modeling_interface',
        'cftime',
        'esmvaltool',
        'grpc4bmi>=0.2.12,<0.3',
        'hydrostats',
        'matplotlib',
        'numpy',
        'pandas',
        'pyoos',
        'python-dateutil',
        'ruamel.yaml',
        'scipy',
        'xarray',
    ],
    packages=find_packages(include=('ewatercycle', 'ewatercycle.*')),
    package_data={
        "": ["*.yaml"],
    },
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords=[
        'ewatercycle',
        'FAIR',
        'BMI',
        'Geoscience',
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Hydrology',
        'Typing :: Typed',
    ],
    extras_require={
        'dev':  [
            # Test
            'deepdiff',
            'pytest',
            'pytest-cov',
            'pytest-mypy',
            'pytest-runner',
            'types-python-dateutil',
            # Linters
            'isort',
            'prospector[with_pyroma,with_mypy]',
            'pycodestyle',
            'yapf',
            # Dependencies for documentation generation
            'nbsphinx',
            'recommonmark',
            'sphinx',
            'sphinx_rtd_theme',
            # ipython syntax highlighting is required in doc notebooks
            'ipython',
            # release
            'build',
            'twine',
         ],
    }
)
