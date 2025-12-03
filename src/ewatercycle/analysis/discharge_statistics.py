"""Analysis methods for eWaterCycle."""

import pandas as pd


def make_yearly_statistic(data_in: pd.DataFrame) -> pd.DataFrame:
    """Compute yearly statistics (mean by default) from a pandas DataFrame.

    Parameters:
    data_in : pd.DataFrame
        Input DataFrame with a datetime index.

    Returns:
    pd.DataFrame
        Yearly statistics as a pandas DataFrame.
    """
    if not isinstance(data_in, pd.DataFrame):
        msg = "Unsupported input type."
        raise TypeError(msg)
    if not isinstance(data_in.index, pd.DatetimeIndex):
        msg = "DataFrame index must be a pd.DatetimeIndex."
        raise TypeError(msg)

    # Mean, max, min per year
    yearly_mean = data_in.resample("YE").mean().add_suffix("_mean")
    yearly_std  = data_in.resample("YE").std().add_suffix("_std")
    yearly_max  = data_in.resample("YE").max().add_suffix("_max")
    yearly_min  = data_in.resample("YE").min().add_suffix("_min")

    # Cumulative yearly volume in m3
    yearly_volume = (data_in * 86400/(1e9)).resample("YE").sum().add_suffix("_volume(km3)")  # noqa: E501

    #combine
    yearly_stats = pd.concat([
        yearly_mean,
        yearly_std,
        yearly_max,
        yearly_min,
        yearly_volume
        ], axis=1)

    #make index just the year
    yearly_stats.index = yearly_stats.index.year
    return yearly_stats
