###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

Unreleased
**********

`1.0.0`_ (2021-07-21)
*********************

Added
-----

* Documentation

  * Example notebooks
  * Setup guide (`#120 <https://github.com/eWaterCycle/ewatercycle/issues/120>`_)
  * HPC cluster guide

* Forcing generation using `ESMValTool <https://www.esmvaltool.org/>`_ (`#28 <https://github.com/eWaterCycle/ewatercycle/issues/28>`_, `#87 <https://github.com/eWaterCycle/ewatercycle/issues/87>`_,)
* Available parameter sets (`#118 <https://github.com/eWaterCycle/ewatercycle/issues/118>`_)
* `PyMT <https://pymt.readthedocs.io/>`_ inspired interface for following models

  * LISFLOOD
  * MARRMoT M01 and M14
  * PCR-GLOBWB
  * wflow

* Model methods to get and set values based on spatial coordinates (`#53 <https://github.com/eWaterCycle/ewatercycle/issues/53>`_, `#140 <https://github.com/eWaterCycle/ewatercycle/issues/140>`_)
* Model method to get value as a xarray dataset (`#36 <https://github.com/eWaterCycle/ewatercycle/issues/36>`_)
* Containerized models using `grpc4bmi <https://github.com/eWaterCycle/grpc4bmi>`_
* Configuration files for system setup
* Hydrograph plotting (`#54 <https://github.com/eWaterCycle/ewatercycle/issues/54>`_)
* Typings
* iso8601 time format (`#90 <https://github.com/eWaterCycle/ewatercycle/issues/90>`_)

Changed
-------

* GRDC returns Pandas dataframe and metadata dict instead of xarray dataset (`#109 <https://github.com/eWaterCycle/ewatercycle/issues/109>`_)

`0.2.0`_ (2021-03-17)
*********************

Added
-----

* Observations from GRDC and USGS
* Empty Python project directory structure
* Added symlink based data files copier

.. _`0.2.0`: https://github.com/eWaterCycle/ewatercycle/releases/tag/0.2.x-observation_data
.. _1.0.0: https://github.com/eWaterCycle/ewatercycle/compare/0.2.x-observation_data...1.0.0
