from ewatercycle.base.parameter_set import ParameterSet


lisflood_fraser = ParameterSet.from_github(
    org="ec-jrc",
    repo="lisflood-usecases",
    branch="master",
    path="LF_lat_lon_UseCase/",
    name="lisflood_fraser",
    directory="lisflood_fraser",
    config="settings_lat_lon-Run.xml",
    doi="N/A",
    target_model="lisflood",
    supported_model_versions={"20.10"},
)
