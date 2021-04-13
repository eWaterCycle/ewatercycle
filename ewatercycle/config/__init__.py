"""config module.

.. data:: CFG

    eWaterCycle configuration object.

    The configuration is loaded from
    1. ~/.ewatercycle/$XDG_CONFIG_HOME/.ewatercycle/ewatercycle.yaml
    2. ~/.ewatercycle/.config/.ewatercycle/ewatercycle.yaml
    3. /etc/ewatercycle.yaml
    4. Fall back to empty configuration

    The `ewatercycle.yaml` is formatted in YAML and could for example look like

    .. code-block:: yaml

      esmvaltool_config: ~/.esmvaltool/config-user.yml
      grdc_location: /data/grdc
      container_engine: singularity
      singularity_dir: /data/singularity-images
      output_dir: /scratch
      # Created with cd  /data/singularity-images && singularity pull docker://ewatercycle/wflow-grpc4bmi:2020.1.1
      wflow.singularity_images: wflow-grpc4bmi_2020.1.1.sif
      wflow.docker_images: ewatercycle/wflow-grpc4bmi:2020.1.1
"""

from ._config_object import CFG, Config

__all__ = [
    'CFG',
    'Config',
]
