"""Config
******

Configuration of eWaterCycle is done via the
:py:class:`~eWaterCycle.config.Configuration` object. The global configuration can be
imported from the :py:mod:`eWaterCycle` module as :py:data:`~ewatercycle.CFG`:

.. code-block:: python

    >>> from ewatercycle import CFG
    >>> CFG
    Configuration(
        grdc_location=PosixPath('.'),
        container_engine='docker',
        apptainer_dir=PosixPath('.'),
        singularity_dir=None,
        output_dir=PosixPath('.'),
        parameterset_dir=PosixPath('.'),
        parameter_sets={},
        ewatercycle_config=None
    )

By default all values have usable values.

:py:data:`~ewatercycle.CFG` is a `Pydantic model <https://docs.pydantic.dev/usage/models/>`_.
This means that values can be updated like this:

.. code-block:: python

    >>> CFG.output_dir = '~/output'
    >>> CFG.output_dir
    PosixPath('/home/user/output')

Notice that :py:data:`~ewatercycle.CFG` automatically converts the path to an
instance of ``pathlib.Path`` and expands the home directory. All values entered
into the config are validated to prevent mistakes, for example, it will warn you
if you make a typo in the key:

.. code-block:: python

    >>> CFG.output_directory = '/output'
    ValidationError: 1 validation error for Configuration
    output_directory
        extra fields not permitted (type=value_error.extra)


Or, if the value entered cannot be converted to the expected type:

.. code-block:: python

    >>> CFG.output_dir = 123
    ValidationError: 1 validation error for Configuration
    output_dir
        value is not a valid path (type=type_error.path)


By default, the config is loaded from the default location (i.e.
``~/.config/ewatercycle/ewatercycle.yaml``). If it does not exist, it falls back
to the default values. to load a different file:

.. code-block:: python

    >>> CFG.load_from_file('~/my-config.yml')

Or to reload the current config:

.. code-block:: python

    >>> CFG.reload()

.. data:: CFG

eWaterCycle configuration object.

The configuration is loaded from:

 1. ``$XDG_CONFIG_HOME/ewatercycle/ewatercycle.yaml``
 2. ``~/.config/ewatercycle/ewatercycle.yaml``
 3. ``/etc/ewatercycle.yaml``
 4. Fall back to empty configuration

The ``ewatercycle.yaml`` is formatted in YAML and could for example look like:

.. code-block:: yaml

    grdc_location: /data/grdc
    container_engine: apptainer
    apptainer_dir: /data/apptainer-images
    output_dir: /scratch
    # Created with cd  /data/apptainer-images &&
    # apptainer pull docker://ewatercycle/wflow-grpc4bmi:2020.1.1
"""

from ._config_object import (
    CFG,
    SYSTEM_CONFIG,
    USER_HOME_CONFIG,
    Configuration,
    ContainerEngine,
)

__all__ = [
    "CFG",
    "Configuration",
    "ContainerEngine",
    "SYSTEM_CONFIG",
    "USER_HOME_CONFIG",
]
