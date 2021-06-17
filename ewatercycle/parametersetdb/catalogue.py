_PARAMETER_SETS = (
    {
        "name": "lisflood_comparison_study",
        "target_model": "lisflood",
        "doi": "N/A",
        "PathRoot": "/projects/0/wtrcycle/comparison/lisflood_input/Lisflood01degree_masked",
        "MaskMap": "/projects/0/wtrcycle/comparison/recipes_auxiliary_datasets/LISFLOOD/model_mask.nc",
        "config_template": "/projects/0/wtrcycle/comparison/lisflood_input/settings_templates/settings_lisflood.xml",
    },
    {
        "name": "wflow_example_case",
        "target_model": "wflow",
        "doi": "N/A",
        "input_data": "./wflow_example_case_nc/",
        "default_config": "./wflow_example_case_nc/wflow_sbm_NC.ini",
    },
    {
        "name": "pcrglobwb_example_case",
        "target_model": "pcrglobwb",
        "doi": "N/A",
        "input_dir": "./pcrglobwb_example_case",
        "default_config": "./pcrglobwb_example_case/setup.ini",
    },
)


class _ParameterSet:
    """Container object for parameter set options."""

    def __init__(self, name, doi="N/A", target_model="generic", **kwargs):
        self.name = name
        self.doi = doi
        self.target_model = target_model
        for k, v in kwargs.items():
            self.__setattr__(k, v)  # TODO automatic parsing of Paths

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __repr__(self):
        attrs = self.__dict__.copy()
        model = attrs.pop("target_model").capitalize()
        options = ", ".join([f"{k}={v!r}" for k, v in attrs.items()])
        return f"{model}ParameterSet({options})"

    def __str__(self):
        """Nice formatting of parameter set."""
        attrs = self.__dict__.copy()
        model = attrs.pop("target_model").capitalize()
        return "\n".join(
            [
                f"{model} parameterset",
                "--------------------------",
            ]
            + [f"{k}={v!r}" for k, v in attrs.items()]
        )


def available_parameter_sets(target_model):
    return (
        p["name"]
        for p in _PARAMETER_SETS
        if p["target_model"] in [target_model, "generic"]
    )


def get_parameter_set(name: str = None, doi: str = None):
    # check valid input
    if name is None and doi is None:
        raise ValueError("Please specify either the name or the doi")

    # search parametersets
    if name is not None:
        options = next((p for p in _PARAMETER_SETS if p["name"] == name), None)
    elif doi is not None:
        options = next((p for p in _PARAMETER_SETS if p["doi"] == doi), None)

    if options is None:
        raise ValueError(f"No parameter set available with name {name}")

    try:
        parameter_set = _ParameterSet(options)
    except Exception:
        raise ValueError(
            "Failed to fetch parameterset. Please "
            "check with system administrator."
        )

    return parameter_set


def download_parameter_sets():
    raise NotImplementedError(
        "Auto download of parameter sets not yet supported"
    )
