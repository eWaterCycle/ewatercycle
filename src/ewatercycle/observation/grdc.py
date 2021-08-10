import os
from typing import Dict, Tuple, Union
import logging

import pandas as pd
from ewatercycle import CFG
from ewatercycle.util import get_time, to_absolute_path

logger = logging.getLogger(__name__)


def get_grdc_data(station_id: str,
                  start_time: str,
                  end_time: str,
                  parameter: str = 'Q',
                  data_home: str = None,
                  column: str = 'streamflow') -> Tuple[pd.core.frame.DataFrame, Dict[str, Union[str, int, float]]]:
    """Get river discharge data from Global Runoff Data Centre (GRDC).

    Requires the GRDC daily data files in a local directory. The GRDC daily data
    files can be ordered at
    https://www.bafg.de/GRDC/EN/02_srvcs/21_tmsrs/riverdischarge_node.html

    Args:
        station_id: The station id to get. The station id can be found in the
            catalogues at
            https://www.bafg.de/GRDC/EN/02_srvcs/21_tmsrs/212_prjctlgs/project_catalogue_node.html
        start_time: Start time of model in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of model in  UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        parameter: optional. The parameter code to get, e.g. ('Q') discharge,
            cubic meters per second.
        data_home : optional. The directory where the daily grdc data is
            located. If left out will use the grdc_location in the eWaterCycle
            configuration file.
        column: optional. Name of column in dataframe. Default: "streamflow".

    Returns:
        grdc data in a dataframe and metadata.

    Examples:
        .. code-block:: python

            from ewatercycle.observation.grdc import get_grdc_data

            df, meta = get_grdc_data('6335020', '2000-01-01T00:00Z', '2001-01-01T00:00Z', data_home='.')
            df.describe()
                     streamflow
            count   4382.000000
            mean    2328.992469
            std	    1190.181058
            min	     881.000000
            25%	    1550.000000
            50%	    2000.000000
            75%	    2730.000000
            max	   11300.000000

            meta
            {'grdc_file_name': '/home/myusername/git/eWaterCycle/ewatercycle/6335020_Q_Day.Cmd.txt',
            'id_from_grdc': 6335020,
            'file_generation_date': '2019-03-27',
            'river_name': 'RHINE RIVER',
            'station_name': 'REES',
            'country_code': 'DE',
            'grdc_latitude_in_arc_degree': 51.756918,
            'grdc_longitude_in_arc_degree': 6.395395,
            'grdc_catchment_area_in_km2': 159300.0,
            'altitude_masl': 8.0,
            'dataSetContent': 'MEAN DAILY DISCHARGE (Q)',
            'units': 'm³/s',
            'time_series': '1814-11 - 2016-12',
            'no_of_years': 203,
            'last_update': '2018-05-24',
            'nrMeasurements': 'NA',
            'UserStartTime': '2000-01-01T00:00Z',
            'UserEndTime': '2001-01-01T00:00Z',
            'nrMissingData': 0}
    """
    if data_home:
        data_path = to_absolute_path(data_home)
    elif CFG["grdc_location"]:
        data_path = to_absolute_path(CFG["grdc_location"])
    else:
        raise ValueError(
            f'Provide the grdc path using `data_home` argument '
            f'or using `grdc_location` in ewatercycle configuration file.'
            )

    if not data_path.exists():
        raise ValueError(f'The grdc directory {data_path} does not exist!')

    # Read the raw data
    raw_file = data_path / f"{station_id}_{parameter}_Day.Cmd.txt"
    if not raw_file.exists():
        raise ValueError(f'The grdc file {raw_file} does not exist!')

    # Convert the raw data to an xarray
    metadata, df = _grdc_read(
        raw_file,
        start=get_time(start_time).date(),
        end=get_time(end_time).date(),
        column=column)

    # Add start/end_time to metadata
    metadata["UserStartTime"] = start_time
    metadata["UserEndTime"] = end_time

    # Add number of missing data to metadata
    metadata["nrMissingData"] = _count_missing_data(df, column)

    # Shpw info about data
    _log_metadata(metadata)

    return df, metadata


def _grdc_read(grdc_station_path, start, end, column):
    with open(
            grdc_station_path, 'r', encoding='cp1252',
            errors='ignore') as file:
        data = file.read()

    metadata = _grdc_metadata_reader(grdc_station_path, data)

    allLines = data.split('\n')
    header = 0
    for i, line in enumerate(allLines):
        if line.startswith('# DATA'):
            header = i + 1
            break

    # Import GRDC data into dataframe and modify dataframe format
    grdc_data = pd.read_csv(
        grdc_station_path,
        encoding='cp1252',
        skiprows=header,
        delimiter=';',
        parse_dates=['YYYY-MM-DD'],
        na_values='-999')
    grdc_station_df = pd.DataFrame(
        {column: grdc_data[' Value'].values},
        index = grdc_data['YYYY-MM-DD'].values,
        )
    grdc_station_df.index.rename('time', inplace=True)

    # Select GRDC station data that matches the forecast results Date
    grdc_station_select = grdc_station_df.loc[start:end]

    return metadata, grdc_station_select


def _grdc_metadata_reader(grdc_station_path, allLines):
    """
    # Initiating a dictionary that will contain all GRDC attributes.
    # This function is based on earlier work by Rolf Hut.
    # https://github.com/RolfHut/GRDC2NetCDF/blob/master/GRDC2NetCDF.py
    # DOI: 10.5281/zenodo.19695
    # that function was based on earlier work by Edwin Sutanudjaja
    # from Utrecht University.
    # https://github.com/edwinkost/discharge_analysis_IWMI
    # Modified by Susan Branchett
    """

    # initiating a dictionary that will contain all GRDC attributes:
    attributeGRDC = {}

    # split the content of the file into several lines
    allLines = allLines.replace("\r", "")
    allLines = allLines.split("\n")

    # get grdc ids (from files) and check their consistency with their
    # file names
    id_from_file_name = int(
        os.path.basename(grdc_station_path).split(".")[0].split("_")[0])
    id_from_grdc = None
    if id_from_file_name == int(allLines[8].split(":")[1].strip()):
        id_from_grdc = int(allLines[8].split(":")[1].strip())
    else:
        print("GRDC station " + str(id_from_file_name) + " (" +
              str(grdc_station_path) + ") is NOT used.")

    if id_from_grdc is not None:

        attributeGRDC["grdc_file_name"] = str(grdc_station_path)
        attributeGRDC["id_from_grdc"] = id_from_grdc

        try:
            attributeGRDC["file_generation_date"] = \
                str(allLines[6].split(":")[1].strip())
        except:
            attributeGRDC["file_generation_date"] = "NA"

        try:
            attributeGRDC["river_name"] = \
                str(allLines[9].split(":")[1].strip())
        except:
            attributeGRDC["river_name"] = "NA"

        try:
            attributeGRDC["station_name"] = \
                str(allLines[10].split(":")[1].strip())
        except:
            attributeGRDC["station_name"] = "NA"

        try:
            attributeGRDC["country_code"] = \
                str(allLines[11].split(":")[1].strip())
        except:
            attributeGRDC["country_code"] = "NA"

        try:
            attributeGRDC["grdc_latitude_in_arc_degree"] = \
                float(allLines[12].split(":")[1].strip())
        except:
            attributeGRDC["grdc_latitude_in_arc_degree"] = "NA"

        try:
            attributeGRDC["grdc_longitude_in_arc_degree"] = \
                float(allLines[13].split(":")[1].strip())
        except:
            attributeGRDC["grdc_longitude_in_arc_degree"] = "NA"

        try:
            attributeGRDC["grdc_catchment_area_in_km2"] = \
                float(allLines[14].split(":")[1].strip())
            if attributeGRDC["grdc_catchment_area_in_km2"] <= 0.0:
                attributeGRDC["grdc_catchment_area_in_km2"] = "NA"
        except:
            attributeGRDC["grdc_catchment_area_in_km2"] = "NA"

        try:
            attributeGRDC["altitude_masl"] = \
                float(allLines[15].split(":")[1].strip())
        except:
            attributeGRDC["altitude_masl"] = "NA"

        try:
            attributeGRDC["dataSetContent"] = \
                str(allLines[20].split(":")[1].strip())
        except:
            attributeGRDC["dataSetContent"] = "NA"

        try:
            attributeGRDC["units"] = str(allLines[22].split(":")[1].strip())
        except:
            attributeGRDC["units"] = "NA"

        try:
            attributeGRDC["time_series"] = \
                str(allLines[23].split(":")[1].strip())
        except:
            attributeGRDC["time_series"] = "NA"

        try:
            attributeGRDC["no_of_years"] = \
                int(allLines[24].split(":")[1].strip())
        except:
            attributeGRDC["no_of_years"] = "NA"

        try:
            attributeGRDC["last_update"] = \
                str(allLines[25].split(":")[1].strip())
        except:
            attributeGRDC["last_update"] = "NA"

        try:
            attributeGRDC["nrMeasurements"] = \
                int(str(allLines[38].split(":")[1].strip()))
        except:
            attributeGRDC["nrMeasurements"] = "NA"

    return attributeGRDC


def _count_missing_data(df, column):
    """Return number of missing data."""
    return df[column].isna().sum()


def _log_metadata(metadata):
    """Print some information about data."""
    coords = (
        metadata['grdc_latitude_in_arc_degree'],
        metadata['grdc_longitude_in_arc_degree']
        )
    message = (
        f"GRDC station {metadata['id_from_grdc']} is selected. "
        f"The river name is: {metadata['river_name']}."
        f"The coordinates are: {coords}."
        f"The catchment area in km2 is: {metadata['grdc_catchment_area_in_km2']}. "
        f"There are {metadata['nrMissingData']} missing values "
        f"during {metadata['UserStartTime']}_{metadata['UserEndTime']} at this station. "
        f"See the metadata for more information.")
    logger.info("%s", message)
