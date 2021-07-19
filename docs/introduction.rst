Introduction
============

Philosophy
----------

In general eWaterCycle tries to strike a balance between making it easy to use
standard available elements of an experiment (datasets, models, analysis
algorithms), and supplying custom elements. This does mean that a simple usecase
sometimes requires slightly more lines of code than strictly nescessary, for the
sake of making it easy to adapt this code to more complex and/or custom
usecases.

Glossary
--------

- Experiment: A notebook running one or more hydrological models and producing a scientific result.
- Model: Software implementation of an algorithm. Note this excludes data required for this model.
- Forcing: all time dependent data needed to run a model, and that is not impacted by the model.
- Model Parameters: fixed parameters (depth of river, land use, irrigation channels, dams). Considered constant during a model run.
- Parameter Set: File based collection of parameters for a certain model, resolution, and possibly area.
- Model instance: single running instance of a model, including all data required, and with a current state.
