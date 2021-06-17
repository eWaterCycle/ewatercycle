eWaterCycle platform tutorial
=============================

This is a small tutorial of the eWaterCycle platform, showing the
concepts in the eWaterCycle platform, and how these are generally used.
The experiment shown in this notebook is a straigtforward model run
leading to a hydrograph.

**NOTE: At the moment this tutorial is not functional.**

eWaterCycle platform concept
----------------------------

In general eWaterCycle tries to strike a balance between making it easy
to use standard available elements of an experiment (datasets, models,
analysis algorithms), and supplying custom elements. This does mean that
a simple usecase sometimes requires slightly more lines of code than
strictly nescessary, for the sake of making it easy to adapt this code
to more complex and/or custom usecases.

Glossary
--------

-  Experiment: A notebook running one or more hydrological models and
   producing a scientific result.
-  Model: Software implementation of an algorithm. Note this excludes
   data required for this model.
-  Forcing: all time dependent data needed to run a model, and that is
   not impacted by the model.
-  Model Parameters: fixed parameters (depth of river, land use,
   irrigation channels, dams). Considered constant during a model run.
-  Parameter Set: File based collection of parameters for a certain
   model, resolution, and possibly area.
-  Model instance: single running instance of a model, including all
   data required, and with a current state.

Ingredients of a model instance
-------------------------------

To create a model instance, we need to select: - A model. - Forcing
(usually converted to a model specific format). - Parameters for this
model. Some models come with default parameters, most must be explicitly
given a parameter set on creation of an instance. Parameters can be
overriden in the setup function.

When creating a model instance, eWaterCycle will supply the following: -
A configuration file for the model. This is generated from a template
for that specific model. - A container for the model. This is found in
the collection of model containers

Configuration
-------------

To be able to find all needed data and models eWaterCycle comes with a
configuration object. This configuration contains system settings for
eWaterCycle (which container technology to use, where is the data
located, etc). In general these should not need to be changed by the
user for a specific experiment, and ideally a user would never need to
touch this configuration on a properly managed system.

Note: a path on the local filesystem is always denoted as “dir” (short
for directory), instead of folder, path, or location. Especially
location can be confusing in the context of geospatial modeling.

ESMValTool configuration
^^^^^^^^^^^^^^^^^^^^^^^^

As eWaterCycle relies on ESMValTool for processing forcing data,
configuration for forcing is mostly defered to the esmvaltool
configuration file. What ESMValTool configuration file to use can be
specified in the eWatercycle configuration.

Examples of configuration
^^^^^^^^^^^^^^^^^^^^^^^^^

-  Where is the grdc data stored?
-  What container technology is used (singularity or docker)?
-  Where are the singularity model containers stored locally?
-  Where are the parameter sets stored?
-  Where will the (temporary) output data be stored by default?

.. code:: ipython3

    # this loads the configuration from the default location(s). This should normally be fine
    from ewatercycle import CFG
    
    #This completely unnecessary line loads the configuration file from the default location.
    CFG.load_from_file('~/.ewatercycle/config.yml')
    
    CFG
    
    # Config({
    #    'container_engine': 'docker',
    #    'esmvaltool_config': PosixPath('/home/user/.ewatercycle/esmvaltool-config-user.yml'),
    #    'ewatercycle_config': PosixPath('/home/user/.ewatercycle/config.yml'),
    #    'grdc_data_dir': '/Path/to/grdc/data',
    #    'output_dir': PosixPath('/home/user/ewatercycle-output'),
    #    'singularity_containers_dir': '/home/user/ewatercycle/singularity'
    #    'parameterset_dir': '/home/user/ewatercycle/parameter_sets',

Forcing generation
------------------

eWaterCycle can generate forcing for a model using the ``forcing``
module. This does all the required steps to go from the available
datasets (ERA-5, ERA-Interim, etc) to whatever format the model requires
for forcing. In general the output should match a forcing prepared
“manually” for this model.

As input for the forcing generation the shape of the required forcing
(usually a catchment) is needed. eWaterCycle will derive additiona
information such as a bounding box if this is required by the model
(e.g. in case of a gridded model), and additional options may be
available or even required for some models.

The forcing module generates a ESMValTool recipe using all the arguments
supplied. For most models all computations are done using ESMValTool.
However, for some models (e.g. lisflood) additional computation is done,
as some steps require data and/or code not available in ESMValTool.

The forcing generated is returned in the form of an object with metadata
attached, and the main forcing being stored in a directory. This
directory can either be specified explicitly, or it will be
auto-generated by eWaterCycle from the output dir specified in the
configuration. Some additional functionality is available to analyse the
forcing, most promonently a plotting function to visually inspect the
forcing.

.. code:: ipython3

    import ewatercycle.forcing
    
    forcing = ewatercycle.forcing.generate(
        target_model='wflow', 
        dataset='ERA-Interim', # example of a more advanced case: forcing.findCMIPData(mip=6, exp=historical)
        start_time="2021-05-07T13:32:00Z",
        end_time="2021-12-31T23:59:59Z",
        shape = '/path/to/shapefile.shp',
        model_specific_options = {
            'wflow_dem_file' : '/some/path/to/dem.dem',
            'hype_catchment_delineation' : '/some/other/shapefile'
        },
        #location on the file system where the output will but placed. Optional, otherwise generated.
        directory='/path/to/forcing/output/',
    )
    
    # Calling this function should show a progress bar, or at least auto-hide or auto-scroll the output.

.. code:: ipython3

    forcing.directory
    # path to forcing output (content of the work dir of the esmvaltool output)
    
    forcing.start_time
    # datetime() object
    
    forcing.end_time
    # datetime() object
    
    forcing.dataset
    # 'ERA-Interim', eventually dataset object
    
    forcing.target_model
    # 'wflow'
    
    forcing.shape
    # Shape()
    
    #optional
    forcing.plot()
    # some matplotlib output that shows the forcing
    
    #optional
    forcing.interactive_plot()
    #some geoviews/widget/thingy that shows the forcing
    
    #optional
    forcing.log
    # show some info on how this was generated (the esmvaltool log?)
    
    #optional
    forcing.recipe
    # the esmvaltool recipe, to inspect what was done in the end.

Example Yaml file with forcing metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   target_model: wflow 
   start_time: 2021-05-07T13:32:00Z
   end_time: 2021-12-31T23:59:59Z

   #relative to (and inside) directory of this yaml file
   shape: shapefile.shp
   model_specific_forcing_info:
     # relative to this directory
     forcing_filename: some-filename.nc
     temperature-variable-name: TEMP

Loading existing forcing
------------------------

Existing forcing can also be loaded using a function much like the
forcing generation function

.. code:: ipython3

    import ewatercycle.forcing
    
    #load an existing forcing that was generated manually by some scientist from Deltares
    forcing = ewatercycle.forcing.load_external(
        #location on the file system where the output can be found
        directory='/path/to/forcing/output/',
        target_model='wflow', 
        start_time='2021-05-07T13:32:00Z'
        model_specific_forcing_info = {
            'forcing_filename' : 'some-filename.nc', # relative to forcing directory
            'temperature-variable-name': 'TEMP'
        },
    )
    
    #fetch an existing forcing that was generated with generate
    forcing = ewatercycle.forcing.load(
        #location on the file system where the output can be found (no other options here)
        directory='/path/to/forcing/output/'
    )

Model versions
--------------

eWaterCycle supports a number of models, and new once can be adding
using a straightforward process. These are represented using a Python
Class (e.g. ewatercycle.models.Wflow). Several version of a model may be
available. To help with reproducibility the version of a model must
always be specified when creating a model instance. A class function is
available to retrieve a list of model versions.

.. code:: ipython3

    import ewatercycle.models.Wflow
    
    ewatercycle.models.Wflow.available_versions
    # ["2019.1", "2020.1"]

Parameter Sets
--------------

eWaterCycle allows model parameters to be set once a model instance has
been created. However, as some models require a large number of files
and other settings, it is also possible to pass a ``ParameterSet`` apon
creation of a model instance. Which ParameterSets are available for a
certain model can be requested from the model class.

In general the id determines the location in the collection of parameter
sets available.

.. code:: ipython3

    import ewatercycle.parameter_sets
    
    ewatercycle.parameter_sets.available_parameter_sets(target_model='wflow')
    # ["wflow-30-min-global", "wflow-05-min-rhinemeuse"]
    
    parameter_set = ewatercycle.parameter_sets.get_parameter_set('wflow-30-min-global')
    
    parameter_set.target_model
    # 'wflow'
    
    parameter_set.doi
    # 'https://doi.org/10.1000/182'
    
    parameter_set.id
    # 'wflow-30-min-global'
    
    parameter_set.supported_model_versions
    # ["2019.1", "2020.1"]
    
    parameter_set.directory
    # '/mnt/data/ewatercycle/parameter_sets/wflow/30-min-global'

Creating, setting up, and initializing a model instance
-------------------------------------------------------

Now that we have created a forcing and selected a version of the model
and a parameter set, we can create a model instance. When creating an
instance we will have to select the version of the model to use, a
parameter set, and a forcing. This will all be combined into an instance
object. This can then be inspected for available parameters and default
values, setup to create the configuration file, work_dir containing
input files, and container, and initialized to prepare a model for
running.

The way models are created, setup, and initialized matches PyMT as much
as possible. There is currently no ‘run’ method as this convenance
method makes it harder for users to create a more advanced usecase from
a simple example.

.. code:: ipython3

    import ewatercycle.models
    
    #A parameter set and forcing object must be loaded or found before instanciating a model.
    
    #Creates as model instance from a model version, parameter_set, and forcing
    #version = mandatory
    #parameter set = optional (e.g. MARRMOT does not need one)
    #forcing = mandatory for now. At some point we may want to support feeding forcing to a model
    #while running it using set_variable('temperature') and such.
    model_instance = ewatercycle.models.Wflow(version='2019.1', parameter_set=parameter_set, forcing=forcing)
    
    #using the parameters property all parameter defaults can be obtained.
    #this is possibly a subset of everything that can be configured in the config file of model, and up to the
    #creator of the model class to implement. For non-science settings such as logging settings, or file names
    # for all parameter files it does not always make sense to expose these.
    model_instance.parameters
    #soil_depth: 9 (defaults to value in parameter set e.g. in a config template)
    #start_time="2021-05-07T13:32:00Z" (defaults to start of forcing)
    #end_time="2021-05-07T13:32:00Z" (defaults to end of forcing)
    #not all parameter files can be set, but for some it may make sense.
    #land_mask='some/land/mask/in/the/parameter_set.dem'
    
    #the Setup function does the following:
    #- Create a directory which serves as the current working directory for the mode instance
    #- Creates a configuration file in this working directory based on the settings
    #- Creates a container instance for the exact version of the model requesed
    #- Makes the forcing, parameter set and and working directory available to the container using mounts.
    #- If a model cannot cope with forcing and parameter set outside the working directory it is copied
    #  to the working_directory instead.
    #- Input is mounted read-only, the working directory is mounted read-write.
    #- Setup will complain about incompatible model version, parameter_set, and forcing.
    cfg_file, work_dir = model_instance.setup(
        land_mask='/some/land/mask.dem', # if outside of mounts, add a mount, or copy into working dir, or :'(
        soil_depth=9,
        start_time="2021-05-07T13:32:00Z",
        end_time="2021-05-07T13:32:00Z"
    )
    
    #After setup but before initialize everything is good-to-go, but nothing has been done yet. This is
    #An opportunity to inspect the generated configuration file, and make any changes manually that could not be
    #done through the setup method. Splitting these also makes it easier to run initialize in parallel in case a
    #lot of models are created simultaneously (e.g. when calibrating a model)
    config = configparser.ConfigParser()
    config.read(cfg_file)
    #change config file where needed...
    
    #This function will initialize the model using the files created above. For some models this can take some time.
    model_instance.initialize(cfg_file)

Running a model and getting output
----------------------------------

Once initalized a model_instanced can be used by calling functions for
running a single timestep (``update``), setting variables, and getting
variables. Besides the rather lowlevel BMI functions several convenience
functions are also available. These returns objects that make sense for
the type of values returned, such as pandas DataFram and xarray
DataArray or Dataset.

.. code:: ipython3

    #example storing all output of a certain field.
    output = []
    while model_instance.time < model_instance.end_time:
        
        # Update the model (takes a few seconds per timestep)
        model_instance.update() 
        
        #store entire discharge field
        discharge = model.get_value_as_xarray('Discharge')
        output.append(discharge)
            
        # Show progress
        print(reference.time, end="\r")  # "\r" clears the output before printing the next timestamp
        
    result = xarray.merge(output)
    
    result
    #xarray with full output of discharge field

.. code:: ipython3

    #example storing a timeseries for a single location of a certain field
    
    #some location of interest within the model
    output_latitude = 55.4
    output_longitude = 20.0
    
    simulated_discharge = pd.DataFrame(index='time', columns=['discharge'])
    while model_instance.time < model_instance.end_time:
        
        # Update the model (takes a few seconds per timestep)
        model_instance.update() 
        
        # Track discharge at station location
        discharge = model_instance.get_value_at_location('Discharge', latitude=output_latitude, longitude=output_longitude, method='nearest')
        simulated_discharge.append({"time":reference.time, "discharge": discharge})
        
        # Show progress
        print(model_instance.time, end="\r")  # "\r" clears the output before printing the next timestamp
        
    model_output
    #nice table of all dischage values over time for a single location

Analyzing the results
---------------------

Once a model has run we can analyse the result. For this example we will
assume a DataFrame was created with values over time for a certain
location for which GRDC station data is available

.. code:: ipython3

    #Read GRDC data
    
    import ewatercycle.observation.grdc
    
    grdc_station_id = 4147380
    
    #This function automatically fetches the location of the GRDC data from the configuration file
    #Start and end dates are fetched from the model instance
    observations = ewatercycle.observation.grdc.get_grdc_data(
        station_id=grdc_station_id,
        start_date=model_instance.start_time.date(),
        end_date=model_instance.end_time.date(),
    )
    observations
    #xarray containing grdc data

.. code:: ipython3

    #Combine simulated and observated discharge into a single dataframe
    
    import pandas
     
    simulated_discharge_df = pandas.DataFrame(
        {'simulation': model_output}, index=timestamps
    )
    observations_df = observations.streamflow.to_dataframe().rename(
        columns={'streamflow': 'observation'}
    )
    discharge = simulated_discharge_df.join(observations_df)
    discharge
    
    #table with simulated and observed discharge

.. code:: ipython3

    #Plot hydrograph
    
    import ewatercycle.analysis
    
    #todo: also add forcing to this hydrograph in some smart way
    ewatercycle.analysis.hydrograph(
        discharge=discharge,
        reference='observation',
    )
    
    #nice hydrograph

.. code:: ipython3

    #finalize the model.
    #as a side effect also destroys the container
    model_instance.finalize()
