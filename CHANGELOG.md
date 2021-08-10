# Change Log

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).
Formatted as described on [https://keepachangelog.com](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.1.1] (2021-08-10)

### Fixed

- Zenodo DOI

## [1.1.0] (2021-08-10)

### Added

- Column name argument to `get_grdc_data()` ([#190](https://github.com/eWaterCycle/ewatercycle/issues/190))
- Copy to clipboard button to documentation ([#216](https://github.com/eWaterCycle/ewatercycle/issues/216))

### Changed

- Compatible with ESMValTool 2.3 . Older versions (<2.3) of ESMValTool are no longer supported. ([#219](https://github.com/eWaterCycle/ewatercycle/issues/219))
- README, CONTRIBUTING, CHANGELOG reformated from RestructedText to Markdown ([#199](https://github.com/eWaterCycle/ewatercycle/issues/199))

### Fixed

- ParameterSet can be outside CFG['parametersets_dir'] ([#217](https://github.com/eWaterCycle/ewatercycle/issues/217))
- Link to nbviewer ([#202](https://github.com/eWaterCycle/ewatercycle/issues/202))
- Pinned esmpy as temporary workaround for single CPU affinity ([#234](https://github.com/eWaterCycle/ewatercycle/issues/234))

### Removed

- Unused esmvaltool_config field in CFG ([#152](https://github.com/eWaterCycle/ewatercycle/issues/152))

## [1.0.0] (2021-07-21)

### Added

- Documentation
  - Example notebooks
  - Setup guide
        ([\#120](https://github.com/eWaterCycle/ewatercycle/issues/120))
  - HPC cluster guide
- Forcing generation using [ESMValTool](https://www.esmvaltool.org/)
    ([\#28](https://github.com/eWaterCycle/ewatercycle/issues/28),
    [\#87](https://github.com/eWaterCycle/ewatercycle/issues/87),)
- Available parameter sets
    ([\#118](https://github.com/eWaterCycle/ewatercycle/issues/118))
- [PyMT](https://pymt.readthedocs.io/) inspired interface for
    following models
  - LISFLOOD
  - MARRMoT M01 and M14
  - PCR-GLOBWB
  - wflow
- Model methods to get and set values based on spatial coordinates
    ([\#53](https://github.com/eWaterCycle/ewatercycle/issues/53),
    [\#140](https://github.com/eWaterCycle/ewatercycle/issues/140))
- Model method to get value as a xarray dataset
    ([\#36](https://github.com/eWaterCycle/ewatercycle/issues/36))
- Containerized models using
    [grpc4bmi](https://github.com/eWaterCycle/grpc4bmi)
- Configuration files for system setup
- Hydrograph plotting
    ([\#54](https://github.com/eWaterCycle/ewatercycle/issues/54))
- Typings
- iso8601 time format
    ([\#90](https://github.com/eWaterCycle/ewatercycle/issues/90))

### Changed

- GRDC returns Pandas dataframe and metadata dict instead of xarray
    dataset
    ([\#109](https://github.com/eWaterCycle/ewatercycle/issues/109))

## [0.2.0] (2021-03-17)

### Added

- Observations from GRDC and USGS
- Empty Python project directory structure
- Added symlink based data files copier

[Unreleased]: https://github.com/eWaterCycle/ewatercycle/compare/1.1.1...HEAD
[1.1.1]: https://github.com/eWaterCycle/ewatercycle/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/eWaterCycle/ewatercycle/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/eWaterCycle/ewatercycle/compare/0.2.x-observation_data...1.0.0
[0.2.0]: https://github.com/eWaterCycle/ewatercycle/releases/tag/0.2.x-observation_data
