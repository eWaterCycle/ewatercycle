FROM mcr.microsoft.com/devcontainers/miniconda

COPY conda-lock.yml /tmp/conda-lock.yml

RUN conda install mamba conda-lock -n base -c conda-forge -y

RUN conda-lock install -n ewatercycle /tmp/conda-lock.yml

SHELL ["conda", "run", "-n", "ewatercycle", "/bin/bash", "-c"]

# To build docs, pandoc is needed
RUN mamba install -y pandoc

RUN echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc \
    && echo "conda activate ewatercycle" >> ~/.bashrc
