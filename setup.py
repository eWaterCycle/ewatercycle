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
        'esmvaltool',
        'ruamel.yaml',
        'xarray',
        'numpy',
        'pandas',
        'pyoos',
        'basic_modeling_interface',
        # TODO subclosses of ewatercycle.models.abstract.AbstractModel will need
        # 'grpc4bmi>=0.2.12,<0.3',
    ],
    packages=find_packages(),
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    extras_require={
        'dev':  [
            # Test
            'deepdiff',
            'pytest',
            'pytest-cov',
            'pytest-mypy',
            # Linters
            'pycodestyle',
            'prospector[with_pyroma,with_mypy]',
            'yapf',
            'isort',
            # dependency for `pytest`
            'pytest-runner',
            # dependencies for documentation generation
            'sphinx',
            'recommonmark',
            'sphinx_rtd_theme',
         ],
    }
)
