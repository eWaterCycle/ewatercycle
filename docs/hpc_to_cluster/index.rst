Migrate eWaterCycle HPC environment to Cluster environment Documentation
========================================================================


========
Contents
========

.. toctree::
   :maxdepth: 2
   preperation.rst
   login.rst
   :caption: Contents:


=======================================
Migrate from HPC to Cluster (Cartesius) 
=======================================
Familiarize yourself with Linux by reading this simple guide:

- https://maker.pro/linux/tutorial/basic-linux-commands-for-beginners

*************************
Migratation Preparation
*************************

**1. Create Github repository**

Start by creating a Github repository to store (only) your code by following these guides:

- https://docs.github.com/en/github/getting-started-with-github/set-up-git 
- https://docs.github.com/en/github/getting-started-with-github/create-a-repo

**2. Create Conda environment.yml** (not required)

For ease of transfer it can be helpful to create a environment.yml file. This file contains a list of all the packages you use for running code. This is good practice because it allows users of your Github repository to quickly install the necessary package requirements. 

- https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#create-env-file-manually

**3. Copy files from HPC to Cartesius**

To copy files from the eWaterCycle HPC to Cartesius the following command example can be used:

- ``scp -r {YourUserNameOnTheHPC}@jupyter.ewatercycle.org:/mnt/{YourUserNameOnTheHPC}/{PathToFolder}/ /home/{YourUserNameOnTheCartesius}/{PathToFolder}/``

When prompted, enter your eWaterCycle HPC password.

********************
Login to Cartesius
********************

**1. VPN Connection**

Cluster computer hosting institutes have a strict policy on which IP-addresses are allowed to connect with the Cluster (Cartesius). For this reason you need to first establish a VPN connection to your University or Research Institute that has a whitelisted IP-address.

**2. MobaXterm**
 
To connects with Cartesius a SSH client is required. One such free client is MobaXterm and can be downloaded here: https://mobaxterm.mobatek.net/. 

- After installation open the client and click on the session tab (top left), click on SSH, at remote host fill in "cartesius.surfsara.nl", tick the specify username box, fill in your Cartesius username and click OK (bottom). Fill in the cartesius password when prompted.

**3. Login Node & Compute Node**

Once you are logged in you are on the login node. This node should not be used to run scripts as it is only a portal to communicate with the compute nodes running on the background (the actual computers). The compute nodes are where you will do the calculations. We communicate with compute nodes using Bash (.sh) scripts. This will be explained later. 

**4. Home Directory & Scratch Directory**

When you login you are directed to your Home Directory: 

- ``/home/{YourUserNameOnTheCartesius}/``

The Home Directory has slower diskspeeds than the Scratch Directory. The Scratch Directory needs to be created using the following commands:

- ``cd /scratch-shared/``
- ``mkdir {YourUserNameOnTheCartesius}``

You can now access the Scratch Directory at ``/scratch/shared/{YourUserNameOnTheCartesius}/``. Best practice is to modify your code such that it first copies all the required files (excluding code) to the Scratch Directory, followed by running the code, after completion copying the files back to the Home Directory, and cleaning up the Scratch Directory.

*************************
First Run preparations
*************************
**1. Clone Github repository**

Clone Github repository containing scripts using:
 
- ``git clone https://github.com/example_user/example_repo``


**2. Install MiniConda**

Go to home directory: 

- ``cd /home/username/``

Download MiniConda:

- ``wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh``

Install MiniConda:

- ``bash Miniconda3-latest-Linux-x86_64.sh``

**Restart the connection with Cartesius**

- ``conda update conda``

**3. Create Conda environment**

Create a Conda enviroment and install required packages following the description: 

https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-with-commands

Make sure that Jupyter Lab is installed in the Conda environment:

- ``conda activate {YourEnvironmentName}``
- ``conda install -c conda-forge jupyterlab`` 

Install GRPC4BMI:

- ``pip install grpc4bmi==0.2.*``

**4. Create Singularity Container**

On Cartesius, Docker requires root access and can therefore not be used. Singularity is similar to, and integrates well with Docker.         It also requires root access, but it is pre-installed on the compute nodes on Cartesius.

The first step to run the model on a compute node is thus to use singularity to create a Singularity image (``.sif`` file) based on the Docker image. This is done with (note the ``srun`` command to access the compute node):

- ``srun -N 1 -t 40 -p short singularity build --disable-cache ewatercycle-wflow-grpc4bmi.sif docker://ewatercycle/wflow-grpc4bmi:latest``

This is an example for the wflow_sbm model, change to the correct Docker container:

-  ``docker://ewatercycle/{model}-grpc4bmi:{version}``

**5. Adjust code to run Singularity container**

Code should be adjusted to run Singularity instead of Docker following:
::

    from grpc4bmi.bmi_client_singularity import BmiClientSingularity

    model = BmiClientSingularity(image='ewatercycle-wflow-grpc4bmi.sif', input_dir=input_dir, output_dir=output_dir)
    ...

**6. Adjust code to use Scratch directory**

Before running the model copy the model instance to the scratch directory: 

``/scratch-shared/{YourUsernameOnTheCartesius}/``

Run the model from this directory and copy the output back to the home directory:

``/home/{YourUsernameOnTheCartesius}/``

Cleanup files in the scratch directory.


**************************************
Submitting Jupyter Job on Cluster node
**************************************
Here we briefly explain general SBATCH parameters and how to launch a Jupyter Lab environment on Cartesius. Start by opening a text editor on Cartesius (e.g. ``vim``) or (easier) your local machine (e.g. notepad). Copy the following text inside your text editor, edit the Conda environment name, and save as **run_jupyter_on_cartesius.sh** (make sure the extension is ``.sh``):
::
    
    #!/bin/bash

    # Serve a jupyter lab environment from a compute node on Cartesius
    # usage: sbatch run_jupyter_on_compute_node.sh

    # SLURM settings
    #SBATCH -J jupyter_lab
    #SBATCH -t 09:00:00
    #SBATCH -N 1
    #SBATCH -p normal
    #SBATCH --output=slurm_%j.out
    #SBATCH --error=slurm_%j.out

    # Use an appropriate conda environment
    . ~/miniconda3/etc/profile.d/conda.sh
    conda activate {YourEnvironmentName}

    # Some security: stop script on error and undefined variables
    set -euo pipefail

    # Specify (random) port to serve the notebook
    port=8123
    host=$(hostname -s)

    # Print command to create ssh tunnel in log file
    echo -e "

    Command to create ssh tunnel (run from another terminal session on your local machine):
    ssh -L ${port}:${host}:${port} $(whoami)@cartesius.surfsara.nl
    Below, jupyter will print a number of addresses at which the notebook is served.
    Due to the way the tunnel is set up, only the latter option will work. 
    It's the one that looks like 
    http://127.0.0.1:${port}/?token=<long_access_token_very_important_to_copy_as_well>
    Copy this address in your local browser and you're good to go

    Starting notebooks server
    **************************************************
    "
    
    # Start the jupyter lab session
    
    jupyter lab --no-browser --port ${port} --ip=${host}

**Explanation of SBATCH Parameters**

- ``#SBATCH -J jupyter_lab``

Here you can set the job name.

- ``#SBATCH -t 09:00:00``

Here you specify job runtime. On the Cartesius we have a budget, each half hour cpu runtime costs 1 point on the budget. A Node consists of 24 cores meaning that the specified runtime (9 hours) costs 24*2*9 points on the budget.

- ``#SBATCH -N 1``

Specifies the amount of nodes used by the run, keep at default value of 1.

- ``#SBATCH -p normal``

Specifies the type of Node, keep at default value of "normal".

- ``#SBATCH --output=slurm_%j.out``

Specifies the location and name of the job log file.

- More information on SBATCH parameters can be found here: https://userinfo.surfsara.nl/systems/cartesius/usage/batch-usage

**Specifying job runtime**

Good practice for calculating job runtime is by for example running a model first for 1 year, calculate the time it takes. Multiply it by the total amount of years for your study. Add a time buffer of around 10-20 percent. 

- For example: 1 year takes 2 hours, total run is 10 years, 20 hours total, add time buffer, estimated runtime equals 22-24 hours.

**Running the bash (.sh) script**

Enter this command to run the bash script:

- ``sbatch run_jupyter_on_cartesius.sh`` 

(If you get DOS and UNIX linebreak errors, run the following command:)

- ``dos2unix run_jupyter_on_cartesius.sh``



**Job control**

To view which jobs are running you can enter:

- ``squeue -u {YourUserNameOnTheCartesius}`` 

To cancel a running job you can enter:

- ``scancel {jobID}`` 

More information on job control can be found here: https://userinfo.surfsara.nl/systems/lisa/user-guide/creating-and-running-jobs#interacting

=====================================
Launching Jupyter Lab on Cluster Node
=====================================

**1. Open Slurm output log file**

- Open slurm output log file by double clicking in the file browser or by using a text editor (``vim``) and read the output carefully.

**2. Create ssh tunnel between local machine and cluster**

To create a ssh connection between your local machine and the cluster you need to open a command prompt interface on your local machine. For example ``PowerShell`` or ``cmd`` on Windows. 

- copy the line ``ssh -L ${port}:${host}:${port} $(whoami)@cartesius.surfsara.nl`` from the slurm log file (not the bash script) into the command prompt and run.

**3. Connect through browser**

- Open a browser (e.g. Chrome) and go to the url: ``localhost:8123/lab``

**4. Enter the access token** 

- Copy the access token from the slurm otput log file and paste in the browser at access token or password. 

You have now succesfully launched a Jupyter Lab environment on a cluster node.