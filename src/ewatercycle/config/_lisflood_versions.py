"""Versions of Lisflood container images."""

from ewatercycle.container import VersionImages

version_images: VersionImages = {
    "20.10": {
        "docker": "ewatercycle/lisflood-grpc4bmi:20.10",
        "singularity": "ewatercycle-lisflood-grpc4bmi_20.10.sif",
    }
}
