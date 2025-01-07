# ewatercycle

![image](https://github.com/eWaterCycle/ewatercycle/raw/main/docs/examples/logo.png)

A Python package for running hydrological models.

[![Test CI](https://github.com/eWaterCycle/ewatercycle/actions/workflows/test.yml/badge.svg)](https://github.com/eWaterCycle/ewatercycle/actions/workflows/test.yml)
[![Lint CI](https://github.com/eWaterCycle/ewatercycle/actions/workflows/lint.yml/badge.svg)](https://github.com/eWaterCycle/ewatercycle/actions/workflows/lint.yml)
[![Build CI](https://github.com/eWaterCycle/ewatercycle/actions/workflows/build.yml/badge.svg)](https://github.com/eWaterCycle/ewatercycle/actions/workflows/build.yml)
[![codecov](https://codecov.io/gh/eWaterCycle/ewatercycle/graph/badge.svg?token=dAZma01eVz)](https://codecov.io/gh/eWaterCycle/ewatercycle)
[![Documentation Status](https://readthedocs.org/projects/ewatercycle/badge/?version=latest)](https://ewatercycle.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/ewatercycle)](https://pypi.org/project/ewatercycle/)
[![image](https://img.shields.io/badge/fair--software.eu-%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8B-yellow)](https://fair-software.eu)
[![image](https://zenodo.org/badge/DOI/10.5281/zenodo.5119389.svg)](https://doi.org/10.5281/zenodo.5119389)
[![Research Software Directory Badge](https://img.shields.io/badge/rsd-ewatercycle-00a3e3.svg)](https://www.research-software.nl/software/ewatercycle)
[![SQAaaS badge shields.io](https://img.shields.io/badge/sqaaas%20software-silver-lightgrey)](https://api.eu.badgr.io/public/assertions/1iy8I58zRvm7P9en2q0Egg "SQAaaS silver badge achieved")
[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/eWaterCycle/ewatercycle)

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
curl -o conda-lock.yml https://raw.githubusercontent.com/eWaterCycle/ewatercycle/main/conda-lock.yml
conda install mamba conda-lock -n base -c conda-forge -y
conda-lock install --no-dev -n ewatercycle
conda activate ewatercycle
```

The ewatercycle package is installed with

```shell
pip install ewatercycle
```

The ewatercycle package ships without any models. Models are packaged in [plugins](https://ewatercycle.readthedocs.io/en/latest/plugins.html). To install all endorsed plugins use

```shell
pip install ewatercycle-hype ewatercycle-lisflood ewatercycle-marrmot ewatercycle-pcrglobwb ewatercycle-wflow ewatercycle-leakybucket
```

Besides installing software you will need to create a configuration
file, download several data sets and get container images. See the
[system setup
chapter](https://ewatercycle.readthedocs.org/en/latest/system_setup.html)
for instructions.

## Usage

Example using the [Marrmot M14
(TOPMODEL)](https://github.com/wknoben/MARRMoT/blob/master/MARRMoT/Models/Model%20files/m_14_topmodel_7p_2s.m)
hydrological model on Rhine catchment to generate forcing, run it
and produce a hydrograph.

<details>

<summary>
In condensed code:

```python
forcing = ewatercycle.forcing.sources['MarrmotForcing'].generate(...)
model = ewatercycle.models.sources['MarrmotM14'](forcing)
model.setup(...)
model.initialize()
while (model.time < model.end_time):
    model.update()
    value = model.get_value_as_xarray('flux_out_Q')
model.finalize()
ewatercycle.analysis.hydrograph(...)
```

(Click to see real code)
</summary>
In real code:

```python
import ewatercycle.analysis
import ewatercycle.forcing
import ewatercycle.models
import ewatercycle.observation.grdc
from ewatercycle.testing.fixtures import rhine_shape
import shapefile
import xarray as xr

forcing = ewatercycle.forcing.sources['MarrmotForcing'].generate(
    dataset='ERA5',
    start_time='2010-01-01T00:00:00Z',
    end_time='2010-12-31T00:00:00Z',
    shape=rhine_shape()
)

model = ewatercycle.models.sources['MarrmotM14'](version='2020.11', forcing=forcing)

cfg_file, cfg_dir = model.setup(
    threshold_flow_generation_evap_change=0.1,
)

model.initialize(cfg_file)

# flux_out_Q unit conversion factor from mm/day to m3/s
sf = shapefile.Reader(rhine_shape())
area = sf.record(0)['SUB_AREA'] * 1e6 # from shapefile in m2
conversion_mmday2m3s = 1 / (1000 * 24 * 60 * 60)
conversion = conversion_mmday2m3s * area

simulated_discharge = []
while (model.time < model.end_time):
    model.update()
    simulated_discharge.append(
        model.get_value_as_xarray('flux_out_Q')
    )

observations_ds = ewatercycle.observation.grdc.get_grdc_data(
    station_id=6335020,  # Rees, Germany
    start_time=model.start_time_as_isostr,
    end_time=model.end_time_as_isostr,
    column='observation',
)

# Combine the simulated discharge with the observations
sim_da = xr.concat(simulated_discharge, dim='time') * conversion
sim_da.name = 'simulated'
discharge = xr.merge([sim_da, observations_ds["observation"]]).to_dataframe()
discharge = discharge[["observation", "simulated"]].dropna()

ewatercycle.analysis.hydrograph(discharge, reference='observation')

model.finalize()
```

</details>

More examples can be found in the plugins listed in the
[documentation](https://ewatercycle.readthedocs.io/en/latest/plugins.html).

## Contributing

If you want to contribute to the development of ewatercycle package,
have a look at the [contribution guidelines](CONTRIBUTING.md).

## License

Copyright (c) 2018 - 2024, Netherlands eScience Center & Delft University of
Technology

Apache Software License 2.0
