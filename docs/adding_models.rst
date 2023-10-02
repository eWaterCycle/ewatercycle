Adding models to eWaterCycle
############################

eWaterCycle has been designed to make it easy to use hydrological models. Using
a model doesn't require much technical expertise, so researchers can focus on
scientific discovery instead. By contrast, adding new models to eWaterCycle
requires a deep understanding of the technologies used to build the system and
the models of which it is comprised.

There are roughly three steps to adding a model to eWaterCycle:

1. :ref:`BMI model`
2. :ref:`eWaterCycle plugin`
3. :ref:`Custom forcing` (Optional)

Use the flowchart below to determine which steps are required for your model.

.. raw:: html
    :file: _static/flowchart_ewatercycle.excalidraw.svg

.. _BMI model:

Create a model which exposes the Basic Model Interface (BMI)
************************************************************

Models in eWaterCycle follow the `Basic Model
Interface <https://bmi.readthedocs.io>`_. You can either write a model that
directly exposes this interface, but the more common use case is to add a
wrapper around an existing model.

The `https://github.com/eWaterCycle/leakybucket-bmi <https://github.com/eWaterCycle/leakybucket-bmi>`_ repository contains a simple example of a BMI model.
It can be used as a template for your own model.

The following BMI methods are called by the eWaterCycle library
and should be implemented:

* ``initialize()``
* ``finalize()``
* ``update()``
* ``get_current_time()``
* ``get_end_time()``
* ``get_grid_type()``
* ``get_grid_rank()``
.. To convert flat array to xarray or get/set value at coord
* ``get_grid_shape()``
* ``get_grid_size()``
* ``get_grid_x()``
* ``get_grid_y()``
* ``get_output_var_names()``
* ``get_start_time()``
* ``get_time_step()``
.. To convert time to a datetime object
* ``get_time_units()``
* ``get_value_at_indices()``
* ``get_value()``
* ``get_var_grid()``
.. To reserve a correctly sized array for output
* ``get_var_itemsize()``
* ``get_var_nbytes()``
* ``get_var_type()``
* ``set_value_at_indices()``
* ``set_value()``

.. _eWaterCycle plugin:

Add the model as eWaterCycle plugin
***********************************

Models in eWaterCycle are added as plugins. A plugin is a Python package.
The `https://github.com/eWaterCycle/ewatercycle-plugin/tree/leakybucket <https://github.com/eWaterCycle/ewatercycle-plugin/tree/leakybucket>`_ repo contains a simple example of a plugin.
It can be used as a template for your own plugin.

.. _Custom forcing:

Custom forcing
==============

If your model can use generic forcing data
(:py:class:`~ewatercycle.base.forcing.GenericDistributedForcing` or :py:class:`~ewatercycle.base.forcing.GenericLumpedForcing`), you can skip this section.

If your model needs custom forcing data, you need to create your own forcing class.

The forcing class should sub class :py:class:`~ewatercycle.base.forcing.DefaultForcing`.

In the class you have to define attributes for the forcing files your model will need.

To use a ESMValTool recipe you have to implement the :py:meth:`~ewatercycle.base.forcing.DefaultForcing._build_recipe` method.
It should return a :py:class:`~ewatercycle.esmvaltool.models.Recipe` object which can be build using the
:py:class:`~ewatercycle.esmvaltool.builder.RecipeBuilder` class.
For example if your model only needs precipitation you can implement the method like this:

.. code-block:: python

  from ewatercycle.forcing import RecipeBuilder

  ...

  @classmethod
  def _build_recipe(cls,
      start_time: datetime,
      end_time: datetime,
      shape: Path,
      dataset: Dataset | str | dict = "ERA5",
  ):
      return (
        RecipeBuilder()
        .start(start_time.year)
        .end(end_time.year)
        .shape(shape)
        .dataset(dataset)
        .add_variable("pr")
        .build()
      )

If your ESMValTool recipe needs additional arguments you can add and document them by implementing the :py:meth:`~ewatercycle.base.forcing.DefaultForcing.generate` method like
so

.. code-block:: python

    @classmethod
    def generate(
      cls,
      <arguments of DefaultForcing>,
      my_argument: str,
    ):
        """Generate forcing data for my model.

        Args:
            <arguments of DefaultForcing>
            my_argument: My argument
        """
        return super().generate(
            <arguments of DefaultForcing>,
            my_argument=my_argument,
        )


The recipe output is mapped to the forcing class arguments with the :py:meth:`~ewatercycle.base.forcing.DefaultForcing._recipe_output_to_forcing_arguments` method.
If you want to change the mapping you can override this method.

If you do not want to use ESMValTool to generate recipes you can override the :py:meth:`~ewatercycle.base.forcing.DefaultForcing.generate` method.

To list your forcing class in :py:const:`ewatercycle.forcing.sources` you have to register in the `ewatercycle.forcings` entry point group.
It can then be imported with

.. code-block:: python

  from ewatercycle.forcings import sources

  forcing = source['MyForcing'](
    ...
  )
