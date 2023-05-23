from ewatercycle.base.parameter_set import ParameterSet


lisflood_fraser = ParameterSet.from_github(
    repo='https://github.com/ec-jrc/lisflood-usecases/tree/master/LF_lat_lon_UseCase',
    name="lisflood_fraser",
    directory="lisflood_fraser",
    config="settings_lat_lon-Run.xml",
    doi="N/A",
    target_model="lisflood",
    supported_model_versions={"20.10"},
)
