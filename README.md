# ewatercycle

![image](https://github.com/eWaterCycle/ewatercycle/raw/main/docs/examples/logo.png)

A Python package for running hydrological models.

[![image](https://github.com/eWaterCycle/ewatercycle/actions/workflows/ci.yml/badge.svg)](https://github.com/eWaterCycle/ewatercycle/actions/workflows/ci.yml)
[![image](https://sonarcloud.io/api/project_badges/measure?project=eWaterCycle_ewatercycle&metric=alert_status)](https://sonarcloud.io/dashboard?id=eWaterCycle_ewatercycle)
[![image](https://sonarcloud.io/api/project_badges/measure?project=eWaterCycle_ewatercycle&metric=coverage)](https://sonarcloud.io/component_measures?id=eWaterCycle_ewatercycle&metric=coverage)
[![Documentation Status](https://readthedocs.org/projects/ewatercycle/badge/?version=latest)](https://ewatercycle.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/ewatercycle)](https://pypi.org/project/ewatercycle/)
[![image](https://img.shields.io/badge/fair--software.eu-%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8B-yellow)](https://fair-software.eu)
[![image](https://zenodo.org/badge/DOI/10.5281/zenodo.5119389.svg)](https://doi.org/10.5281/zenodo.5119389)
[![Research Software Directory Badge](https://img.shields.io/badge/rsd-ewatercycle-00a3e3.svg)](https://www.research-software.nl/software/ewatercycle)
[![SQAaaS badge shields.io](https://img.shields.io/badge/sqaaas%20software-silver-lightgrey)](https://api.eu.badgr.io/public/assertions/1iy8I58zRvm7P9en2q0Egg "SQAaaS silver badge achieved")

The eWaterCycle package makes it easier to use hydrological models
without having intimate knowledge about how to install and run the
models.

- Uses container for running models in an isolated and portable way
    with [grpc4bmi](https://github.com/eWaterCycle/grpc4bmi)
- Generates rain and sunshine required for the model using
    [ESMValTool](https://www.esmvaltool.org/)
- Supports observation data from [GRDC or
    USGS](https://ewatercycle.readthedocs.io/en/latest/observations.html)
- Exposes [simple
    interface](https://ewatercycle.readthedocs.io/en/latest/user_guide.html)
    to quickly get up and running

## Install

The ewatercycle package needs some geospatial non-python packages to
generate forcing data. It is preferred to create a Conda environment to
install those dependencies:

```shell
wget https://raw.githubusercontent.com/eWaterCycle/ewatercycle/main/environment.yml
conda install mamba -n base -c conda-forge -y
mamba env create --file environment.yml
conda activate ewatercycle
```

The ewatercycle package is installed with

```shell
pip install ewatercycle
```

The ewatercycle package ships without any models. Models are packaged in [plugins](https://ewatercycle.readthedocs.io/en/latest/plugins.html). To install all endorsed plugins use

```shell
pip install ewatercycle-hype ewatercycle-lisflood ewatercycle-marrmot ewatercycle-pcrglobwb ewatercycle-wflow  ewatercycle-leakybucket
```

Besides installing software you will need to create a configuration
file, download several data sets and get container images. See the
[system setup
chapter](https://ewatercycle.readthedocs.org/en/latest/system_setup.html)
for instructions.

## Usage

Example using the [Marrmot M14
(TOPMODEL)](https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Model%20files/m_14_topmodel_7p_2s.m)
hydrological model on Merrimack catchment to generate forcing, run it
and produce a hydrograph.

```python
import pandas as pd
import ewatercycle.analysis
import ewatercycle.forcing
import ewatercycle.models
import ewatercycle.observation.grdc

forcing = ewatercycle.forcing.generate(
    target_model='marrmot',
    dataset='ERA5',
    start_time='2010-01-01T00:00:00Z',
    end_time='2010-12-31T00:00:00Z',
    shape='Merrimack/Merrimack.shp'
)

model = ewatercycle.models.MarrmotM14(version="2020.11", forcing=forcing)

cfg_file, cfg_dir = model.setup(
    threshold_flow_generation_evap_change=0.1,
    leakage_saturated_zone_flow_coefficient=0.99,
    zero_deficit_base_flow_speed=150.0,
    baseflow_coefficient=0.3,
    gamma_distribution_phi_parameter=1.8
)

model.initialize(cfg_file)

observations_df = ewatercycle.observation.grdc.get_grdc_data(
    station_id=4147380,
    start_time=model.start_time_as_isostr,
    end_time=model.end_time_as_isostr,
    column='observation',
).observation.to_dataframe()

simulated_discharge = []
timestamps = []
while (model.time < model.end_time):
    model.update()
    value = model.get_value('flux_out_Q')[0]
    # flux_out_Q unit conversion factor from mm/day to m3/s
    area = 13016500000.0  # from shapefile in m2
    conversion_mmday2m3s = 1 / (1000 * 24 * 60 * 60)
    simulated_discharge.append(value * area * conversion_mmday2m3s)
    timestamps.append(model.time_as_datetime.date())
simulated_discharge_df = pd.DataFrame({'simulated': simulated_discharge}, index=pd.to_datetime(timestamps))

ewatercycle.analysis.hydrograph(simulated_discharge_df.join(observations_df), reference='observation')

model.finalize()
```

More examples can be found in the plugins listed in the
[documentation](https://ewatercycle.readthedocs.io/en/latest/plugins.html).

## Contributing

If you want to contribute to the development of ewatercycle package,
have a look at the [contribution guidelines](CONTRIBUTING.md).

## License

Copyright (c) 2018 - 2024, Netherlands eScience Center & Delft University of
Technology

Apache Software License 2.0
