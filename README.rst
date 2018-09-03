################################################################################
ewatercycle.parametersetdb
################################################################################

Python utilities to gather input files for running a hydrology model

.. image:: https://travis-ci.org/eWaterCycle/parametersetdb.svg?branch=master
    :target: https://travis-ci.org/eWaterCycle/parametersetdb

.. image:: https://sonarcloud.io/api/project_badges/measure?project=ewatercycle-parametersetdb&metric=alert_status
    :target: https://sonarcloud.io/dashboard?id=ewatercycle-parametersetdb

.. image:: https://sonarcloud.io/api/project_badges/measure?project=ewatercycle-parametersetdb&metric=coverage
    :target: https://sonarcloud.io/component_measures?id=ewatercycle-parametersetdb&metric=coverage

.. image:: https://readthedocs.org/projects/ewatercycle-parametersetdb/badge/?version=latest
    :target: https://ewatercycle-parametersetdb.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

Install
-------

.. code-block:: bash

    pip install git+https://github.com/eWaterCycle/parametersetdb.git#egg=ewatercycle-parametersetdb


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

If you want to contribute to the development of ewatercycle_parametersetdb,
have a look at the `contribution guidelines <CONTRIBUTING.rst>`_.

License
*******

Copyright (c) 2018, Netherlands eScience Center & Delft University of Technology

Apache Software License 2.0
