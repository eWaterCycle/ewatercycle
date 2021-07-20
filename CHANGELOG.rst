###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

Unreleased
**********

`1.0.0`_ (2021-07-22)
*********************

Added
-----

* Forcing generation using `ESMValTool <https://www.esmvaltool.org/>`_ (`#28 <https://github.com/eWaterCycle/ewatercycle/issues/28>`_, `#87 <https://github.com/eWaterCycle/ewatercycle/issues/87>`_,)
* `PyMT <https://pymt.readthedocs.io/>`_ inspired interface for following models
  * LISFLOOD
  * MARRMoT M01 and M14
  * PCR-GLOBWB
  * wflow
* Containerized models using `grpc4bmi <https://github.com/eWaterCycle/grpc4bmi>`_
* Configuration file for system setup like available parameter sets (`#118 <https://github.com/eWaterCycle/ewatercycle/issues/110>`_)
* Hydrograph plotting (`#54 <https://github.com/eWaterCycle/ewatercycle/issues/54>`_)
* Typings
* Documentation
  * Example notebooks
  * Setup guide (`#120 <https://github.com/eWaterCycle/ewatercycle/issues/120>`_)
  * HPC cluster guide
* iso8601 time format (`#90 <https://github.com/eWaterCycle/ewatercycle/issues/90>`_)

Changed
-------

* GRDC returns Pandas dataframe and metadata dict instead of xarray dataset (``_)

`0.2.0`_ (2021-03-17)
*********************

Added
-----

* Observations from GRDC and USGS
* Empty Python project directory structure
* Added symlink based data files copier

.. _`0.2.0`: https://github.com/eWaterCycle/ewatercycle/releases/tag/0.2.x-observation_data
.. _1.0.0: https://github.com/eWaterCycle/ewatercycle/compare/0.2.x-observation_data...1.0.0
