Adding models to eWaterCycle
############################

eWaterCycle has been designed to make it easy to use hydrological models. Using
a model doesn't require much technical expertise, so researchers can focus on
scientific discovery instead. By contrast, adding new models to eWaterCycle
requires a deep understanding of the technologies used to build the system and
the models of which it is comprised.

So far, the process for adding new models to eWaterCycle has been coordinated by
the system developers. Should you wish to add a new model yourself, it is
advisable to contact us well in advance (e.g. through GitHub), so we may be able
to provide assistance. In the meantime, we're working towards a process where
adding models to eWaterCycle can be carried out by the eWaterCycle community.

.. note::
  The instructions on this page are still rudimentary. If you would like to help
  us improve them, please don't hesitate to get in touch by opening an issue.

There are roughly five steps to adding a model to eWaterCycle:

1. :ref:`BMI model`
2. :ref:`Make container`
3. :ref:`Make recipe`
4. :ref:`Add to Python package`
5. :ref:`Add to platform`

If you want to add a new version of a model the procedure is roughly the
same, but you can skip several steps. If you are already familiar with the
eWaterCycle bits and pieces, you can refer to :ref:`New versions` for a
condensed version of the necessary steps.

.. _BMI model:

Create a model which exposes the Basic Model Interface (BMI)
************************************************************

Models in eWaterCycle follow the `Basic Model
Interface <https://bmi.readthedocs.io>`_. You can either write a model that
directly exposes this interface, but the more common use case is to add a
wrapper around an existing model. For more information please follow the
instructions at https://bmi.readthedocs.io/.

.. _Make container:

Package the model together with grpc4bmi server in a docker container
*********************************************************************

In eWaterCycle models are stored in Docker container images, which can be shared
through DockerHub. Because Docker is not always available on compute clusters,
we also create Singularity images. Besides the model code, the container image
should install grpc4bmi server as an entrypoint to enable communication with the
model from outside of the container. We use standardized image names including a
unique version number for the model. See the section on :ref:`versions<New
versions>` below for more info on model versions.

Concretely, these are the steps you should follow:

* Create Docker container image named ``ewatercycle/<model>-grpc4bmi:<version>``
  with grpc4bmi server running as entrypoint. For detailed instructions and
  examples, please see
  https://grpc4bmi.readthedocs.io/en/latest/container/building.html
* Host Docker container image on `Docker Hub
  <https://hub.docker.com/u/ewatercycle>`_
* Create Singularity image from Docker with ``singularity build
  ./ewatercycle-<model>-grpc4bmi_<version>.sif
  docker://ewatercycle/<model>-grpc4bmi:<version>``

.. _Make recipe:

Write (or find) an ESMValTool recipe to generate forcing
********************************************************

.. note::

  This step is not strictly necessary to run the model. You may choose to postpone
  this step until after you've successfully completed the subsequent steps, but
  until then you will not have the possibility to generate custom forcing data.

In eWaterCycle we use ESMValTool to generate forcing data for our models.
ESMValTool provides a standardized workflow to read and process climate data
from various sources. In this way we can easily convert e.g. raw climate model
output to a format that our hydrological model understands. Ideally, all
hydrological models should use standardized input data formats (we suggest
"generic lumped" and "generic distributed" as the two main types of forcing
data). However, in reality most models use slightly different formats, variables,
terminologies, et cetera. Therefore, custom ESMValTool recipes are available for
most (if not all) models in eWaterCycle, and there is a good chance that you
will have to add another one for your model.

For the available recipes in ESMValTool, see
https://docs.esmvaltool.org/en/latest/recipes/recipe_hydrology.html.


ESMValTool has a nice tutorial that guides you through the steps to write a new
recipe:
https://esmvalgroup.github.io/ESMValTool_Tutorial/06-preprocessor/index.html. If
you've not used ESMValTool before, it might be helpful to walk through the
tutorial in its entirety.

To add a new ESMValTool recipe, we recommend starting from an existing
eWaterCycle recipe and modifying it for your needs.

.. _Add to Python package:

Add the model to the eWaterCycle Python package
***********************************************

The eWaterCycle Python package brings together (almost) all components of the
eWaterCycle system. Adding your BMI-enabled model to the eWaterCycle Python
package will make it available for anyone that installs the package. However,
code contributions to the eWaterCycle Python package involve a thorough review
process and it requires a new release of the package for the changes to be
available to others.

To start adding a model to the eWaterCycle Python package, you will need to
install a development version of the code following the instructions in
https://github.com/eWaterCycle/ewatercycle/blob/main/CONTRIBUTING.md.

The following changes have to be made to the code:

* Create model as subclass of ``AbstractModel`` (``src/ewatercycle/models/abstract.py``)
* Import model in ``src/ewatercycle/models/__init__.py``
* Add ``src/ewatercycle/forcing/<model>.py`` (this needs to use the ESMValTool recipe mentioned above).
* Register model in ``src/ewatercycle/forcing/__init__.py:FORCING_CLASSES``
* If model needs a custom parameter set class add it in ``src/ewatercycle/parameter_sets/_<model name>.py``
* Add example parameter set in ``src/ewatercycle/parameter_sets/__init__.py``
* Write tests
* Write example notebook
* Add model to ``docs/conf.py``
* Add container image to :doc:`system_setup`
* Add container image to infrastructure data preparation scripts_

At this point, you should be able to use the model with your local development
version of the eWaterCycle Python package. However, in order to make it
available to other users, you need to create a pull request on GitHub, and
respond to questions raised in the review process until the PR is approved and
merged. At that point, you can ask the package developers to create a new
release, so that the changes will be available on PyPi. Again, please refer to
the instructions in
https://github.com/eWaterCycle/ewatercycle/blob/main/CONTRIBUTING.md for more
information about the contributing process.

.. _Add to platform:

Make the new model available on a machine that's running eWaterCycle
********************************************************************

At this stage, anyone can see and use your inside eWaterCycle on their own
machine. However, the more interesting and common use case for eWaterCycle is
for it to be hosted on a tailor-made platform. That is, you get access to a
machine with a Jupyter Lab environment, an explorer, and lot's of data readily
available.

In our case, we run the platform on SURF Research Cloud, which is configured
using Ansible as detailed in our `infrastructure repository
<https://github.com/eWaterCycle/infra/>`_.

To make sure that your model will be available on a new or existing platform,
you need to make sure that:

* The latest version of eWaterCycle is installed on that platform
* The singularity image is available on that platform
* The example parameter set is available on that platform

Typically these steps should be performed by platform developers and
maintainers.

For SURF infrastructure specifically, this requires to the following changes.

* Install version/branch of eWaterCycle Python package with new model version on any running virtual machines
* Add Singularity image to storage. In our case, we use a dCache folder ``ewcdcache:/singularity-images/<model>-grpc4bmi_<version>.sif``
* Add container image to infrastructure repository

  * data preparation scripts_
  * `config generation <https://github.com/eWaterCycle/infra/blob/main/roles/ewatercycle/templates/ewatercycle.yaml.j2>`_

* Optionally: Add example parameter set to `explorer catalog <https://github.com/eWaterCycle/TerriaMap/blob/ewatercycle-v8/wwwroot/init/ewatercycle.json>`_. The forcing, parameter set and model image should be available on Jupyter server connected to explorer.

.. _New versions:

Adding a new version of a model
===============================

A model can have different versions. A model version in the eWaterCycle Python
package corresponds to the tag of Docker image and the version in a Singularity
container image filename. The version of the container image should preferably
be one of release versions of the model code. Alternatively the version could be
the name of a feature branch or a date.

Also parameter sets can specify with which versions of a model they are
compatible.

Adding a new version of a model involves the following code changes:

* Add container image to :doc:`system_setup` page by editing ``docs/system_setup.rst``
* In ``src/ewatercycle/models/<model>.py``

  * add new version to ``available_versions`` class property.
  * to ``__init__()`` method add support for new version

* Optionally: Add new version to existing example parameter set or add new parameter set in ``src/ewatercycle/parameter_sets/_<model>.py:example_parameter_sets()``
* Add new version to supported parameter sets in local eWaterCycle config file (``/etc/ewatercycle.yaml`` and ``*/.config/ewatercycle/ewatercycle.yaml``)
* Test it locally
* Create pull request and get it merged
* Create new release of Python package. Done by package maintainers

.. _scripts: https://github.com/eWaterCycle/infra/tree/main/roles/prep_shared_data
