"""Config
******

Configuration of eWaterCycle is done via the :py:class:`~eWaterCycle.config.Config` object.
The global configuration can be imported from the :py:mod:`eWaterCycle` module as :py:data:`~ewatercycle.CFG`:

.. code-block:: python

    >>> from ewatercycle import CFG
    >>> CFG
    Config({'container_engine': None,
            'grdc_location': None,
            'output_dir': None,
            'singularity_dir': None,
            'wflow.docker_image': None,
            'wflow.singularity_image': None})

By default all values are initialized as ``None``.

:py:data:`~ewatercycle.CFG` is essentially a python dictionary with a few extra functions, similar to :py:mod:`matplotlib.rcParams`.
This means that values can be updated like this:

.. code-block:: python

    >>> CFG['output_dir'] = '~/output'
    >>> CFG['output_dir']
    PosixPath('/home/user/output')

Notice that :py:data:`~ewatercycle.CFG` automatically converts the path to an instance of ``pathlib.Path`` and expands the home directory.
All values entered into the config are validated to prevent mistakes, for example, it will warn you if you make a typo in the key:

.. code-block:: python

    >>> CFG['output_directory'] = '~/output'
    InvalidConfigParameter: `output_directory` is not a valid config parameter.

Or, if the value entered cannot be converted to the expected type:

.. code-block:: python

    >>> CFG['output_dir'] = 123
    InvalidConfigParameter: Key `output_dir`: Expected a path, but got 123

By default, the config is loaded from the default location (i.e. ``~/.config/ewatercycle/ewatercycle.yaml``).
If it does not exist, it falls back to the default values.
to load a different file:

.. code-block:: python

    >>> CFG.load_from_file('~/my-config.yml')

Or to reload the current config:

.. code-block:: python

    >>> CFG.reload()

.. data:: CFG

eWaterCycle configuration object.

The configuration is loaded from:

 1. ``~/$XDG_CONFIG_HOME/ewatercycle/ewatercycle.yaml``
 2. ``~/.config/ewatercycle/ewatercycle.yaml``
 3. ``/etc/ewatercycle.yaml``
 4. Fall back to empty configuration

The ``ewatercycle.yaml`` is formatted in YAML and could for example look like:

.. code-block:: yaml

    grdc_location: /data/grdc
    container_engine: singularity
    singularity_dir: /data/singularity-images
    output_dir: /scratch
    # Created with cd  /data/singularity-images && singularity pull docker://ewatercycle/wflow-grpc4bmi:2020.1.1
    wflow.singularity_images: wflow-grpc4bmi_2020.1.1.sif
    wflow.docker_images: ewatercycle/wflow-grpc4bmi:2020.1.1
"""

from ._config_object import CFG, Config, SYSTEM_CONFIG, USER_HOME_CONFIG, DEFAULT_CONFIG

__all__ = [
    'CFG',
    'Config',
    'DEFAULT_CONFIG',
    'SYSTEM_CONFIG',
    'USER_HOME_CONFIG'
]
