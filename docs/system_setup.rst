System setup
============

To use ewatercycle package you need to setup the system with software
and data.

This chapter is for system administators or Research Software Engineers who need to setup a system for the eWatercycle platform.

The setup steps:

1.  `Conda environment <#conda-environment>`__
2.  `Install ewatercycle package <#install-ewatercycle-package>`__
3.  `Configure ESMValTool <#configure-ESMValTool>`__
4.  `Download climate data <#download-climate-data>`__
5.  `Install container engine <#install-container-engine>`__
6.  `Configure ewatercycle <#configure-ewatercycle>`__
7.  `Model container images <#model-container-images>`__
8.  `Download example parameter sets <#download-example-parameter-sets>`__
9.  `Prepare other parameter sets <#prepare-other-parameter-sets>`_
10. `Download example forcing <#download-example-forcing>`__
11. `Download observation data <#download-observation-data>`__

Conda environment
-----------------

The ewatercycle Python package uses a lot of geospatial dependencies
which can be installed easiest using `Conda <https://conda.io/>`__ package
management system.

Instal Conda by using the `miniconda
installer <https://docs.conda.io/en/latest/miniconda.html>`__.

After conda is installed you can install the software dependencies with
a `conda environment
file <https://github.com/eWaterCycle/ewatercycle/blob/master/environment.yml>`__.

.. code:: shell

    wget https://raw.githubusercontent.com/eWaterCycle/ewatercycle/master/environment.yml

.. code:: shell

    conda env create --file environment.yml

.. code:: shell

    conda activate ewatercycle

Do not forget that any terminal or Jupyter kernel should activate the conda environment before the ewatercycle Python package can be used.

Install ewatercycle package
---------------------------

The Python package can be installed using pip

.. code:: shell

    # TODO once released install from PyPi instead of GitHub
    # pip install ewatercycle
    pip install git+https://github.com/eWaterCycle/ewatercycle.git#egg=ewatercycle


Configure ESMValTool
--------------------

ESMValTool is used to generate forcing (temperature, precipitation,
etc.) files from climate data sets for hydrological models. The
ESMValTool has been installed as a dependency of the package.

See https://docs.esmvaltool.org/en/latest/quickstart/configuration.html
how configure ESMValTool

Download climate data
---------------------

The ERA5 and ERA-Interim climate datasets can be used to generate
forcings

ERA5
~~~~

To download ERA5 data files you can use the
`era5cli <https://era5cli.readthedocs.io/>`__ tool.

.. code:: shell

    pip install era5cli

To run the example notebooks the hourly ERA5 data files for year 1990
and 1991 and for variables: pr, psl, tas, taxmin, tasmax, tdps, uas,
vas, rsds, rsdt and fx orog need to be downloaded with

.. code:: shell

    # TODO is era5cli command is correct?
    cd <ESMValTool raw directory>
    era5cli hourly --startyear 1990 --endyear 1991 --variables pr psl tas taxmin tasmax tdps uas vas rsds rsdt orog
    cd -

.. code:: shell

    # TODO cmorize files?

ERA-Interim
~~~~~~~~~~~

ERA-Interim has been superseeded by ERA5, but could be useful for
reproduction studies and its smaller size. The ERA-Interim data files
can be downloaded at
https://www.ecmwf.int/en/forecasts/datasets/reanalysis-datasets/era-interim

Installing a container engine requires root permission on the machine.

Install container engine
------------------------

In ewatercycle package the hydrological models are run in containers
with engines like `Singularity <https://singularity.lbl.gov/>`__ or
`Docker <https://www.docker.com/>`__. At least Singularity or Docker
should be installed.

Singularity
~~~~~~~~~~~

Install Singularity using
`instructions <https://singularity.hpcng.org/user-docs/master/quick_start.html>`__.

Docker
~~~~~~

Install Docker using
`instructions <https://docs.docker.com/engine/install/>`__. Docker
should be configured so it can be `called without
sudo <https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user>`__

Configure ewatercycle
---------------------

The ewatercycle package simplifies the API by reading some of the
directories and other configurations from a configuration file.

The configuration can be set in Python with

.. code:: ipython3

    import logging
    logging.basicConfig(level=logging.INFO)
    import ewatercycle
    import ewatercycle.parameter_sets
    # Which container engine is used to run the hydrological models
    ewatercycle.CFG['container_engine'] = 'singularity'  # or 'docker'
    # If container_engine==singularity then where can the singularity images files (*.sif) be found.
    ewatercycle.CFG['singularity_dir'] = './singularity-images'
    # Directory in which output of model runs is stored. Each model run will generate a sub directory inside output_dir
    ewatercycle.CFG['output_dir'] = './'
    # Where can GRDC observation files (<station identifier>_Q_Day.Cmd.txt) be found.
    ewatercycle.CFG['grdc_location'] = './grdc-observations'
    # Where can parameters sets prepared by the system administator be found
    ewatercycle.CFG['parameterset_dir'] = './parameter-sets'
    # Where is the configuration saved or loaded from
    ewatercycle.CFG['ewatercycle_config'] = './ewatercycle.yaml'

and then written to disk with

.. code:: ipython3

    ewatercycle.CFG.save_to_file()

Later it can be loaded by using:

.. code:: ipython3

    ewatercycle.CFG.load_from_file('./ewatercycle.yaml')

To make the ewatercycle configuration load by default for current user
it should be copied to ``~/.config/ewatercycle/ewatercycle.yaml`` .

To make the ewatercycle configuration available to all users on the
system it should be copied to ``/etc/ewatercycle.yaml`` .

Configuration file for Cartesius system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users part of the ewatercycle project on the Cartesius system of
SURFSara can use the following configuration file:

.. code:: yaml

   container_engine: singularity
   singularity_dir: /projects/0/wtrcycle/singularity-images
   output_dir: /scratch/shared/ewatercycle
   grdc_location: /projects/0/wtrcycle/GRDC
   parameterset_dir: /projects/0/wtrcycle/parameter-sets

Configuration file for ewatecycle Jupyter machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On systems constructed with ewatercycle application on SURF Research
Cloud can use the following configuration file:

.. code:: yaml

   container_engine: singularity
   singularity_dir: /mnt/data/singularity-images
   output_dir: /scratch
   grdc_location: /mnt/data/GRDC
   parameterset_dir: /mnt/data/parameter-sets

Model container images
----------------------

As hydrological models run in container their container images should be
made available on the system.

The names of the images can be found in the ``ewatercycle.models.*``
classes.

Docker
~~~~~~

Docker images will be downloaded with ``docker pull``:

.. code:: shell

    docker pull ewatercycle/lisflood-grpc4bmi:20.10
    docker pull ewatercycle/marrmot-grpc4bmi:2020.11
    docker pull ewatercycle/pcrg-grpc4bmi:setters
    docker pull ewatercycle/wflow-grpc4bmi:2020.1.1
    # TODO

Singularity
~~~~~~~~~~~

Singularity images should be stored in configured directory
(``ewatercycle.CFG['singularity_dir']``) and can build from Docker with:

.. code:: ipython3

    !cd {ewatercycle.CFG['singularity_dir']}
    !singularity build ewatercycle-lisflood-grpc4bmi.sif docker://ewatercycle/lisflood-grpc4bmi:latest
    !singularity build ewatercycle-pcrg-grpc4bmi.sif docker://ewatercycle/pcrg-grpc4bmi:latest
    !singularity build ewatercycle-marrmot-grpc4bmi.sif docker://ewatercycle/marrmot-grpc4bmi:latest
    !singularity build ewatercycle-wflow-grpc4bmi.sif docker://ewatercycle/wflow-grpc4bmi:latest
    !cd -

Download example parameter sets
-------------------------------

To quickly run the models it is advised to setup a example parameter
sets for each model.

.. code:: ipython3

    ewatercycle.parameter_sets.download_example_parameter_sets()


.. parsed-literal::

    INFO:ewatercycle.parameter_sets._example:Downloading example parameter set wflow_rhine_sbm_nc to /home/verhoes/git/eWaterCycle/ewatercycle/docs/examples/parameter-sets/wflow_rhine_sbm_nc...
    INFO:ewatercycle.parameter_sets._example:Download complete.
    INFO:ewatercycle.parameter_sets._example:Adding parameterset wflow_rhine_sbm_nc to ewatercycle.CFG...
    INFO:ewatercycle.parameter_sets._example:Downloading example parameter set pcrglobwb_example_case to /home/verhoes/git/eWaterCycle/ewatercycle/docs/examples/parameter-sets/pcrglobwb_example_case...
    INFO:ewatercycle.parameter_sets._example:Download complete.
    INFO:ewatercycle.parameter_sets._example:Adding parameterset pcrglobwb_example_case to ewatercycle.CFG...
    INFO:ewatercycle.parameter_sets._example:Downloading example parameter set lisflood_fraser to /home/verhoes/git/eWaterCycle/ewatercycle/docs/examples/parameter-sets/lisflood_fraser...
    INFO:ewatercycle.parameter_sets._example:Download complete.
    INFO:ewatercycle.parameter_sets._example:Adding parameterset lisflood_fraser to ewatercycle.CFG...
    INFO:ewatercycle.parameter_sets:3 example parameter sets were downloaded
    INFO:ewatercycle.config._config_object:Config written to /home/verhoes/git/eWaterCycle/ewatercycle/docs/examples/ewatercycle.yaml
    INFO:ewatercycle.parameter_sets:Saved parameter sets to configuration file /home/verhoes/git/eWaterCycle/ewatercycle/docs/examples/ewatercycle.yaml


Example parameter sets have been downloaded and added to the
configuration file.

.. code:: shell

    cat ./ewatercycle.yaml


.. parsed-literal::

    container_engine: null
    esmvaltool_config: None
    grdc_location: None
    output_dir: None
    parameter_sets:
      lisflood_fraser:
        config: lisflood_fraser/settings_lat_lon-Run.xml
        directory: lisflood_fraser
        doi: N/A
        supported_model_versions: !!set {'20.10': null}
        target_model: lisflood
      pcrglobwb_example_case:
        config: pcrglobwb_example_case/setup_natural_test.ini
        directory: pcrglobwb_example_case
        doi: N/A
        supported_model_versions: !!set {setters: null}
        target_model: pcrglobwb
      wflow_rhine_sbm_nc:
        config: wflow_rhine_sbm_nc/wflow_sbm_NC.ini
        directory: wflow_rhine_sbm_nc
        doi: N/A
        supported_model_versions: !!set {2020.1.1: null}
        target_model: wflow
    parameterset_dir: /home/verhoes/git/eWaterCycle/ewatercycle/docs/examples/parameter-sets
    singularity_dir: None


.. code:: ipython3

    ewatercycle.parameter_sets.available_parameter_sets()


.. parsed-literal::

    ('wflow_rhine_sbm_nc', 'pcrglobwb_example_case', 'lisflood_fraser')



.. code:: ipython3

    parameter_set = ewatercycle.parameter_sets.get_parameter_set('pcrglobwb_example_case')
    parameter_set


.. parsed-literal::

    ParameterSet(name='pcrglobwb_example_case', directory=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/docs/examples/parameter-sets/pcrglobwb_example_case'), config=PosixPath('/home/verhoes/git/eWaterCycle/ewatercycle/docs/examples/parameter-sets/pcrglobwb_example_case/setup_natural_test.ini'), doi='N/A', target_model='pcrglobwb', supported_model_versions={'setters'})

The ``parameter_set`` variable can be passed to a model class
constructor.

Prepare other parameter sets
----------------------------

The example pararmeter sets downloaded in previous section are nice to show off the plaform features, but are a bit small.
To preform more advanced experiments additonal parameter sets are needed.
Users could use :py:class:`ewatercycle.parameter_sets.ParameterSet` to construct parameter sets themselves.
Or they can be made available via :py:func:`ewatercycle.parameter_sets.available_parameter_sets` and :py:func:`ewatercycle.parameter_sets.get_parameter_set` by extending the configuration file (ewatercycle.yaml).

A new parameter set should be added as a key/value pair in the `parameter_sets` map of the configuration file.
The key should be a unique string on the current system.
The value is a dictionary with the following items:

* directory: Location on disk where files of parameter set are stored. If Path is relative then relative to :py:const:`ewatercycle.CFG['parameterset_dir']`.
* config: Model configuration file which uses files from directory. If Path is relative then relative to :py:const:`ewatercycle.CFG['parameterset_dir']`.
* doi: Persistent identifier of parameter set. For a example a DOI for a Zenodo record.
* target_model: Name of model that parameter set can work with
* supported_model_versions: Set of model versions that are supported by this parameter set. If not set then parameter set will be supported by all versions of model

For example the parameter set for PCR-GLOBWB from https://doi.org/10.5281/zenodo.1045339 after downloading and unpacking to `/data/pcrglobwb2_input/` could be added with following config:

.. code:: yaml

    pcrglobwb_example_case:
        directory: /data/pcrglobwb2_input/global_30min/
        config: /data/pcrglobwb2_input/global_30min/iniFileExample/setup_30min_non-natural.ini
        doi: https://doi.org/10.5281/zenodo.1045339
        target_model: pcrglobwb
        supported_model_versions: !!set {setters: null}


Download example forcing
------------------------

To be able to run the Marrmot example notebooks you need a forcing file.
You can use ``ewatercycle.forcing.generate()`` to make it or use an
already prepared `forcing
file <https://github.com/wknoben/MARRMoT/blob/master/BMI/Config/BMI_testcase_m01_BuffaloRiver_TN_USA.mat>`__.

.. code:: shell

    cd docs/examples
    wget https://github.com/wknoben/MARRMoT/blob/master/BMI/Config/BMI_testcase_m01_BuffaloRiver_TN_USA.mat
    cd -

Download observation data
-------------------------

Observation data is needed to calculate metrics of the model performance or plot a hydrograph . The
ewatercycle package can use`Global Runoff Data Centre
(GRDC) <https://www.bafg.de/GRDC>`__ or `U.S. Geological Survey Water
Services (USGS) <https://waterservices.usgs.gov/>`__ data.

The GRDC daily data files can be ordered at
https://www.bafg.de/GRDC/EN/02_srvcs/21_tmsrs/riverdischarge_node.html.

The GRDC files should be stored in ``ewatercycle.CFG['grdc_location']``
directory.
