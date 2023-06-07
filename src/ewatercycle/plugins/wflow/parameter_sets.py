from ewatercycle.base.parameter_set import ParameterSet

wflow_rhine_sbm_nc = ParameterSet.from_github(
    org="openstreams",
    repo="wflow",
    branch="master",
    subfolder="examples/wflow_rhine_sbm_nc",
    directory="wflow_rhine_sbm_nc",
    name="wflow_rhine_sbm_nc",
    config="wflow_sbm_NC.ini",
    doi="N/A",
    target_model="wflow",
    supported_model_versions={"2020.1.1", "2020.1.2", "2020.1.3"},
)
