import scipy.io as sio

def write_config(parameters, 
    period, 
    forcing_file_loc, 
    config_file_loc , 
    model_name="m_01_collie1_1p_1s", 
    solver={
        "name": "createOdeApprox_IE",
        "resnorm_tolerance": 0.1,
        "resnorm_maxiter": 6.0,
        }, 
    store_ini=1500.0):
    """Write model configuration file.

    Adds the model parameters to forcing file for the given period
    and catchment including the spinup year and writes this information
    to a model configuration file.
    """
    # get the forcing that was created with ESMValTool
    #forcing_file = f"marrmot-m01_{forcing}_{catchment}_{PERIOD['spinup'].year}_{PERIOD['end'].year}.mat"
    forcing_data = sio.loadmat(forcing_file_loc, mat_dtype=True)

    # select forcing data
    forcing_data["time_end"][0][0:3] = [
        period["end"].year,
        period["end"].month,
        period["end"].day,
    ]

    # combine forcing and model parameters
    forcing_data.update(
        model_name=model_name,
        parameters=parameters,
        solver=solver,
        store_ini=store_ini,
    )
    
    sio.savemat(config_file_loc, forcing_data)
