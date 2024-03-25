# Change Log

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).
Formatted as described on [https://keepachangelog.com](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Added new forcing classes ([#393](https://github.com/eWaterCycle/ewatercycle/pull/393)):
  - LumpedUserForcing, DistributedUserForcing - have the variable names as an argument, as well as an optional post-processor that can derive addition variables from the downloaded data.
  - LumpedMakkinkForcing, DistributedMakkinkForcing - based on the UserForcing: selects the required variables and computes the Makkink potential evaporation.
- The available models are now stored in `ewatercycle.models.sources`, just like the different forcing sources ([#393](https://github.com/eWaterCycle/ewatercycle/pull/393)).

### Changed
- Internal changes to DefaultForcing: variables are no longer attributes of the class, but are stored under a "filenames" (dict) attribute ([#393](https://github.com/eWaterCycle/ewatercycle/pull/393)).
- Updated the documentation to reflect the changes in the forcing generation ([#393](https://github.com/eWaterCycle/ewatercycle/pull/393)).
- Shapefiles used for generating forcing are now always copied to the output folder, to allow determination of the area to convert mm water depth to m^3 of discharge. ([#393](https://github.com/eWaterCycle/ewatercycle/pull/393)).

## [2.0.0] (2023-10-10)

### Breaking changes

The eWatercycle package no longer contains models and their forcing and/or example parameter sets. Instead, models are now plugins that can be installed separately. See https://ewatercycle.readthedocs.io/en/latest/plugins.html for a list of endorsed plugins.

### Added

- Apptainer support ([#290](https://github.com/eWaterCycle/ewatercycle/issues/290))
- Forcing ((#365)[https://github.com/eWaterCycle/ewatercycle/pull/365]):
  - GenericDistributedForcing class
  - GenericLumpedForcing class
  - Generate from not just ERA5 or ERA-Interim dataset, but any ESMvalTool supported dataset
- Testing helpers for plugins ((#365)[https://github.com/eWaterCycle/ewatercycle/pull/365])

### Changed

- Upgraded BMI version from 0.2 to 2.0 ([#339](https://github.com/eWaterCycle/ewatercycle/pull/339))
    - Model container images using BMI v0.2 are supported see [grpc4bmi docs](https://grpc4bmi.readthedocs.io/en/latest/server/python.html#legacy-version).
- ewatercycle config, forcings and parameter sets now use Pydantic for validation instead of Matplotlib inspired validation. ([#332](https://github.com/eWaterCycle/ewatercycle/issues/332), [#334](https://github.com/eWaterCycle/ewatercycle/pull/334), [#346](https://github.com/eWaterCycle/ewatercycle/pull/346))
- Functions of a model inside a container that return the same result each call are cached with [MemoizedBmi](https://grpc4bmi.readthedocs.io/en/latest/api/grpc4bmi.bmi_memoized.html#grpc4bmi.bmi_memoized.MemoizedBmi) ([#339](https://github.com/eWaterCycle/ewatercycle/pull/339))
- Moved CaseConfig to src/utils.py
- forcing.load_foreign has been superceded by using sources.model(...)
- Forcing ((#365)[https://github.com/eWaterCycle/ewatercycle/pull/365]):
  - Instead of modifying an existing recipe now builds a ESMValTool recipe from scratch using a fluent interface
  - DefaultForcing has overridable class methods for each step of the forcing generation process (build_recipe, run_recipe, recipe_output_to_forcing_arguments).
- eWaterCycleModel.parameters property type is ItemsView instead of dict.
- Rewrote adding models documentation to use the new plugin system ([#383](https://github.com/eWaterCycle/ewatercycle/pull/383)

### Deprecated

- Singularity support ([#290](https://github.com/eWaterCycle/ewatercycle/issues/290))

### Removed

- Models live in their own repository as a eWatercycle plugin. ([#371](https://github.com/eWaterCycle/ewatercycle/issues/371))
- Removed parametersetdb module. XmlConfig moved to lisflood plugin. YamlConfig & IniConfig have been removed.

## [2.0.0] (2023-10-06)

Everthing listed at [2.0.0](2.0.0), but without the adding models part.

## [1.4.1] (2022-12-20)

### Fixed

- PEP 484 prohibits implicit Optional ([#325](https://github.com/eWaterCycle/ewatercycle/pull/325))
- Update of ESMValCore breaks recipes tests ([#325](https://github.com/eWaterCycle/ewatercycle/issues/325))
- Pre-commit hook for flake8 from GitHub instead of GitLab ([#325](https://github.com/eWaterCycle/ewatercycle/pull/325))
- Update of ESMValCore breaks Marrmot forcing generation ([#322](https://github.com/eWaterCycle/ewatercycle/pull/322))
- Forcing generation for Wflow has been fixed ([#321](https://github.com/eWaterCycle/ewatercycle/pull/321))

## [1.4.0] (2022-06-20)

### Added

- delay argument to `ewatercycle.models.Marrmot*.setup()_ ([#303](https://github.com/eWaterCycle/ewatercycle/issues/303))
- Hype forcing generation and model [#308](https://github.com/eWaterCycle/ewatercycle/pull/308)

### Removed

- Python 3.7 support

## [1.3.0] (2022-04-20)

### Added

- Directory argument to `ewatercycle.forcing.generate()` ([#145](https://github.com/eWaterCycle/ewatercycle/issues/145))

### Changed

- Improved performance of forcing generation of LISFLOOD model ([#301](https://github.com/eWaterCycle/ewatercycle/pull/301))

## [1.2.0] (2022-03-28)

### Added

- Evaporation Pre-Processor for the LISFLOOD (Lisvap) to forcing ([#282](https://github.com/eWaterCycle/ewatercycle/issues/282))
- Set number of bars in hydrograph ([#298](https://github.com/eWaterCycle/ewatercycle/pull/298))

## [1.1.4] (2022-01-14)

### Added

- 2020.1.3 version of wflow model ([#270](https://github.com/eWaterCycle/ewatercycle/issues/270))

### Changed

- Replace Cartesius section in system setup docs with Snellius ([#273](https://github.com/eWaterCycle/ewatercycle/issues/273))

### Fixed

- Test suite fails with fresh conda env ([#275](https://github.com/eWaterCycle/ewatercycle/issues/275))
- incompatible numpy typings ([#285](https://github.com/eWaterCycle/ewatercycle/issues/285))

## [1.1.3] (2021-10-18)

### Added

- 2020.1.2 version of wflow model ([#268](https://github.com/eWaterCycle/ewatercycle/pull/268))
- Document how to add a new version of a model ([#266](https://github.com/eWaterCycle/ewatercycle/pull/266))

## [1.1.2] (2021-09-29)

### Added

- Type information according to [PEP-0561](https://www.python.org/dev/peps/pep-0561/)
- Pre-commit hooks and black formatting ([#111](https://github.com/eWaterCycle/ewatercycle/issues/111))

### Changed

- Timeout for model setup set to 5 minutes ([#244](https://github.com/eWaterCycle/ewatercycle/issues/244))
- Use mamba for installation instructions ([#136](https://github.com/eWaterCycle/ewatercycle/issues/136))
- Use [version 1.2.0](https://github.com/citation-file-format/citation-file-format/releases/tag/1.2.0) of CITATION.cff format
- Moved package to src/ ([#228](https://github.com/eWaterCycle/ewatercycle/issues/228))

### Fixed

- Name particle in CITATION.cff ([#204](https://github.com/eWaterCycle/ewatercycle/issues/204))
- Build Sphinx locally with config file ([#169](https://github.com/eWaterCycle/ewatercycle/issues/169))
- Type errors in notebooks ([#262](https://github.com/eWaterCycle/ewatercycle/issues/262))
- Lisflood.finalize() ([#257](https://github.com/eWaterCycle/ewatercycle/issues/257))

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

[Unreleased]: https://github.com/eWaterCycle/ewatercycle/compare/2.0.0...HEAD
[2.0.0]: https://github.com/eWaterCycle/ewatercycle/compare/2.0.0b2...2.0.0
[2.0.0b2]: https://github.com/eWaterCycle/ewatercycle/compare/1.4.1...2.0.0b2
[1.4.1]: https://github.com/eWaterCycle/ewatercycle/compare/1.4.0...1.4.1
[1.4.0]: https://github.com/eWaterCycle/ewatercycle/compare/1.3.0...1.4.0
[1.3.0]: https://github.com/eWaterCycle/ewatercycle/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/eWaterCycle/ewatercycle/compare/1.1.4...1.2.0
[1.1.4]: https://github.com/eWaterCycle/ewatercycle/compare/1.1.3...1.1.4
[1.1.3]: https://github.com/eWaterCycle/ewatercycle/compare/1.1.2...1.1.3
[1.1.2]: https://github.com/eWaterCycle/ewatercycle/compare/1.1.1...1.1.2
[1.1.1]: https://github.com/eWaterCycle/ewatercycle/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/eWaterCycle/ewatercycle/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/eWaterCycle/ewatercycle/compare/0.2.x-observation_data...1.0.0
[0.2.0]: https://github.com/eWaterCycle/ewatercycle/releases/tag/0.2.x-observation_data
