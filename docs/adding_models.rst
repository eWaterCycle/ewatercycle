Adding a model
==============

Integrating a new model into the eWaterCycle system involves the following steps:

* Create model as subclass of ``AbstractModel`` (``src/ewatercycle/models/abstract.py``)
* Import model in ``src/ewatercycle/models/__init__.py``
* Add ``src/ewatercycle/forcing/<model>.py``
* Register model in ``src/ewatercycle/forcing/__init__.py:FORCING_CLASSES``
* Add model to ``docs/conf.py``
* Write example notebook
* Write tests?
* If model needs custom parameter set class add it in ``src/ewatercycle/parameter_sets/_<model name>.py``
* Add example parameter set in ``src/ewatercycle/parameter_sets/__init__.py``
* Add container image to :doc:`system_setup`
* Add container image to infrastructure data preparation scripts_

We will expand this documentation in due time.

Adding a new version of a model
-------------------------------

A model can have different versions.
A version corresponds to a Docker and Singularity container image file.
Also parameter sets can be specify which versions of a model they support.

To add a new version of a model involves the following steps:

* Create Docker container image named ``ewatercycle/<model>-grpc4bmi:<version>`` with `grp4bmi server running as entrypoint <https://grpc4bmi.readthedocs.io/en/latest/container/building.html>`_
* Host Docker container image on `Docker Hub <https://hub.docker.com/u/ewatercycle>`_
* Create Singuliary image from Docker with ``singularity build ./ewatercycle-<model>-grpc4bmi_<version>.sif docker://ewatercycle/<model>-grpc4bmi:<version>``
* Add Singularity image to dCache shared folder ``ewcdcache:/singulairy-images/<model>-grpc4bmi_<version>.sif``

To setup local test infra
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Add container image to :doc:`system_setup`
* Add container image to infrastructure data preparation scripts_

To setup for everybody
~~~~~~~~~~~~~~~~~~~~~~

* In ``src/ewatercycle/models/<model>.py``
  * add new version to ``available_versions`` class property.
  * to ``__init__()`` method add support for new version
* Create release with changes incorpeated or a local install with the branch of the Pull Request
* In any eWaterCycle config file (``/etc/ewatercycle.yaml`` and ``~/.config/ewatercycle/ewatercycle.yaml``) add new version to supported parameter sets.
* Optionally: Add new version to existing example parameter set or add new parameter set in ``src/ewatercycle/parameter_sets/_<model>.py:example_parameter_sets()``

* Optionally: Add example to `explorer catalog <https://github.com/eWaterCycle/TerriaMap/blob/ewatercycle-v8/wwwroot/init/ewatercycle.json>`_. The forcing, parameter set and model image should be available on Jupyter server connected to explorer.

.. _scripts: https://github.com/eWaterCycle/infra/tree/main/roles/prep_shared_data
