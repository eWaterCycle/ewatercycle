from ewatercycle.parameter_set import ParameterSet

wflow_rhine_sbm_nc = ParameterSet.from_github(
    repo='https://github.com/openstreams/wflow/tree/master/examples/wflow_rhine_sbm_nc',
    name="wflow_rhine_sbm_nc",
    # Relative to CFG.parameterset_dir / self.name
    config="wflow_sbm_NC.ini",
    doi="N/A",
    target_model="wflow",
    supported_model_versions={"2020.1.1", "2020.1.2", "2020.1.3"},
)
