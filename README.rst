################################################################################
ewatercycle
################################################################################

A Python package for running hydrological models.

.. image:: https://github.com/eWaterCycle/parametersetdb/actions/workflows/ci.yml/badge.svg
    :target: https://github.com/eWaterCycle/parametersetdb/actions/workflows/ci.yml

.. image:: https://sonarcloud.io/api/project_badges/measure?project=eWaterCycle_ewatercycle&metric=alert_status
    :target: https://sonarcloud.io/dashboard?id=eWaterCycle_ewatercycle

.. image:: https://sonarcloud.io/api/project_badges/measure?project=eWaterCycle_ewatercycle&metric=coverage
    :target: https://sonarcloud.io/component_measures?id=eWaterCycle_ewatercycle&metric=coverage

.. image:: https://readthedocs.org/projects/ewatercycle/badge/?version=latest
    :target: https://ewatercycle.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

Install
-------

The ewatercycle package needs some geospatial non-python packages to generate
forcing data. It is preferred to create a Conda environment to install those
dependencies:

.. code-block:: bash

    wget https://raw.githubusercontent.com/eWaterCycle/ewatercycle/master/environment.yml
    conda env create --file environment.yml
    conda activate ewatercycle

The ewatercycle package is installed with

.. code-block:: bash

    pip install git+https://github.com/eWaterCycle/ewatercycle.git#egg=ewatercycle


Usage
-----

.. code-block:: python

    from ewatercycle.parametersetdb import build_from_urls
    parameter_set = build_from_urls(
        config_format='svn', config_url='https://github.com/ClaudiaBrauer/WALRUS/trunk/demo/data',
        datafiles_format='yaml', datafiles_url="data:text/plain,data: data/PEQ_Hupsel.dat\nparameters:\n  cW: 200\n  cV: 4\n  cG: 5.0e+6\n  cQ: 10\n  cS: 4\n  dG0: 1250\n  cD: 1500\n  aS: 0.01\n  st: loamy_sand\nstart: 367416 # 2011120000\nend: 368904 # 2012020000\nstep: 1\n",
    )
    # Overwrite items in config file
    # parameter_set.config['...']['...'] = '...'
    parameter_set.save_datafiles('./input')
    parameter_set.save_config('config.cfg')

CITATION.cff
------------

* To allow others to cite your software, add a ``CITATION.cff`` file
* It only makes sense to do this once there is something to cite (e.g., a software release with a DOI).
* To generate a CITATION.cff file given a DOI, use `doi2cff <https://github.com/citation-file-format/doi2cff>`_.
* `Relevant section in the guide <https://guide.esciencecenter.nl/software/documentation.html#citation-file>`_

Contributing
************

If you want to contribute to the development of ewatercycle package,
have a look at the `contribution guidelines <CONTRIBUTING.rst>`_.

License
*******

Copyright (c) 2018, Netherlands eScience Center & Delft University of Technology

Apache Software License 2.0
