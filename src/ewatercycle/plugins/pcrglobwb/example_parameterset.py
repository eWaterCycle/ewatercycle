from ewatercycle.parameter_set import ParameterSet

pcrglobwb_rhinemeuse_30min = ParameterSet.from_github(
    # TODO data and ini file are in same repo but different directories
    # for cloning whole repo and 
    # should fix input_dir in ini file
    repo="https://github.com/UU-Hydro/PCR-GLOBWB_input_example/tree/master",
    # Relative to CFG.parameterset_dir
    directory="pcrglobwb_rhinemeuse_30min",
    name="pcrglobwb_rhinemeuse_30min",
    # Relative to CFG.parameterset_dir / self.name
    config="ini_and_batch_files_for_pcrglobwb_course/rhine_meuse_30min_using_input_example/setup_natural_test.ini",
    # DOI of big set on github is very small test set
    doi="https://doi.org/10.5281/zenodo.1045339",
    target_model="pcrglobwb",
    supported_model_versions={"setters"},
)
