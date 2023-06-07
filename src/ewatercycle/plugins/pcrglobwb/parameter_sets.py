from ewatercycle.base.parameter_set import ParameterSet

pcrglobwb_rhinemeuse_30min = ParameterSet.from_github(
    org="UU-Hydro",
    repo="PCR-GLOBWB_input_example",
    branch="master",
    subfolder="RhineMeuse30min",
    # Relative to CFG.paramUU-eterset_dir
    directory="pcrglobwb_rhinemeuse_30min",
    name="pcrglobwb_rhinemeuse_30min",
    # Relative to CFG.parameterset_dir / self.name
    config="ini_and_batch_files/deltares_laptop/setup_natural_test.ini",
    # DOI of big set on github is very small test set
    doi="https://doi.org/10.5281/zenodo.1045339",
    target_model="pcrglobwb",
    supported_model_versions={"setters"},
)
