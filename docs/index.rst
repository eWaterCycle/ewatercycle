.. ewatercycle documentation master file, created by
   sphinx-quickstart on Thu Jun 21 11:07:11 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to ewatercycle's documentation!
=======================================

The eWaterCycle Python package brings together many components from the
`eWaterCycle project <https://www.ewatercycle.org/>`_. An overall goal of this
project is to make hydrological modelling fully reproducible, open, and FAIR.

Modelled after `PyMT <https://pymt.readthedocs.io/en/latest/index.html>`_, it
enables interactively running a model from a Python environment like so:

.. code-block:: python

   from ewatercycle.models import Wflow
   model = Wflow(version="2020.1.1", parameterset=example_parameter_set, forcing=example_forcing)
   cfg_file, cfg_dir = model.setup(end_time="2020-01-01T00:00:00Z")
   model.initialize(cfg_file)

   output = []
   while model.time < model.end_time:
       model.update()
       discharge = model.get_value_at_coords("RiverRunoff", lat=[52.3], lon=[5.2])
       output.append(discharge)

To learn how to use the package, see the `User guide <user_guide.html>`_ and
`example pages <examples.html>`_.

Typically the eWaterCycle platform is deployed on a system that can be accessed
through the browser via JupyterHub, and comes preconfigured with readily
available parameter sets, meteorological forcing data, model images, etcetera.
This makes it possible for researchers to quickly run an experiment without the
hassle of installing a model or creating suitable input data. To learn more
about the system setup, read our `System setup <system_setup.html>`_ page.

In general eWaterCycle tries to strike a balance between making it easy to use
standard available elements of an experiment (datasets, models, analysis
algorithms), and supplying custom elements. This does mean that a simple usecase
sometimes requires slightly more lines of code than strictly nescessary, for the
sake of making it easy to adapt this code to more complex and/or custom
usecases.


Glossary
--------

To avoid miscommunication, here we define explicitly what we mean by some terms
that are commonly used throughout this documentation.

- **Experiment**: A notebook running one or more hydrological models and producing a scientific result.
- **Model**: Software implementation of an algorithm. Note this excludes data required for this model.
- **Forcing**: all time dependent data needed to run a model, and that is not impacted by the model.
- **Model Parameters**: fixed parameters (depth of river, land use, irrigation channels, dams). Considered constant during a model run.
- **Parameter Set**: File based collection of parameters for a certain model, resolution, and possibly area.
- **Model instance**: single running instance of a model, including all data required, and with a current state.

.. toctree::
   :caption: User Guide
   :maxdepth: 2
   :hidden:

   user_guide/00_intro
   user_guide/01_parameter_sets
   user_guide/02_forcing
   user_guide/03_models_obs_analysis

.. toctree::
   :caption: Documentation
   :maxdepth: 2
   :hidden:

   system_setup
   adding_models
   plugins
   infrastructures
   observations
