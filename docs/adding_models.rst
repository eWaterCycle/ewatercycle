Adding a model
==============

Integrating a new model into the eWaterCycle system involves the following steps:

* Create model as subclass of ``AbstractModel`` (``ewatercycle/models/abstract.py``)
* Import model in ``ewatercycle/models/__init__.py``
* Add ``ewatercycle/forcing/<model>.py``
* Register model in ``ewatercycle/forcing/__init__.py:FORCING_CLASSES``
* Add model to ``docs/conf.py``
* Write example notebook
* Write tests?
* If model needs custom parameter set class add it in ``ewatercycle/parameter_sets/_<model name>.py``
* Add example parameter set in ``ewatercycle/parameter_sets/__init__.py``
* Add container image to setup guide

We will expand this documentation in due time.
