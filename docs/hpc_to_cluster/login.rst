==================
Login to Cartesius
==================

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
