"""
Versions of Lisflood container images
"""
from pathlib import Path

version_images = {
    "20.10": {
        "docker": "ewatercycle/lisflood-grpc4bmi:20.10",
        "singularity": "ewatercycle-lisflood-grpc4bmi_20.10.sif",
    }
}


def get_docker_image(version):
    return version_images[version]["docker"]


def get_singularity_image(version, singularity_dir: Path):
    return singularity_dir / version_images[version]["singularity"]
