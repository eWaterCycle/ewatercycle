Observations
============

The eWaterCycle platform supports observations relevant for calibrating and validating models. We currently support USGS and GRDC river discharge observations.

USGS
----

The `U.S. Geological Survey Water Services <https://waterservices.usgs.gov/>`_ provides public discharge data for a large number of US based stations. In eWaterCycle we make use of the `USGS web service <https://waterservices.usgs.gov/test-tools/?service=iv>`_ to automatically retrieve this data.
The Discharge timestamp is corrected to the UTC timezone. Units are converted from cubic feet per second to cubic meter per second.

GRDC
----

The `Global Runoff Data Centre <https://grdc.bafg.de/>`_ provides discharge data for a large number of stations around the world. In eWaterCycle we support GRDC data. This is not downloaded automatically, but required to be present on the infrastructure where the eWaterCycle platform is deployed. By special permission from GRDC our own instance contains data from the ArcticHYCOS and GCOS/GTN-H, GTN-R projects.
