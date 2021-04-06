=======================
Migratation Preparation
=======================

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