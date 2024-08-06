FROM mcr.microsoft.com/devcontainers/miniconda

COPY conda-lock.yml /tmp/conda-lock.yml

RUN conda install mamba conda-lock -n base -c conda-forge -y

RUN conda-lock install -n ewatercycle /tmp/conda-lock.yml

SHELL ["conda", "run", "-n", "ewatercycle", "/bin/bash", "-c"]

# To build docs, pandoc is needed
RUN mamba install -y pandoc

# Env vars set by conda activate ewatercycle
ENV ESMFMKFILE=/opt/conda/envs/ewatercycle/lib/esmf.mk \
    GDAL_DATA=/opt/conda/envs/ewatercycle/share/gdal \
    GDAL_DRIVER_PATH=/opt/conda/envs/ewatercycle/lib/gdalplugins \
    MAGPLUS_HOME=/opt/conda/envs/ewatercycle \
    PROJ_DATA=/opt/conda/envs/ewatercycle/share/proj \
    PROJ_NETWORK=ON \
    UDUNITS2_XML_PATH=/opt/conda/envs/ewatercycle/share/udunits/udunits2.xml \
    XML_CATALOG_FILES="file:///opt/conda/envs/ewatercycle/etc/xml/catalog file:///etc/xml/catalog"
