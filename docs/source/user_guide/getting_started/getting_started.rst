Getting started
===============

Installation of AiiDA-FLEUR
---------------------------
.. _downloading: https://github.com/JuDFTteam/aiida-fleur
.. _AiiDA: https://aiida.readthedocs.io/projects/aiida-core/en/latest
.. _tutorial: https://aiida.readthedocs.io/projects/aiida-core/en/latest/install/installation.html#aiida-profile-setup
.. _needed: https://aiida.readthedocs.io/projects/aiida-core/en/latest/install/prerequisites.html
.. _iffwiki: https://iffwiki.fz-juelich.de/Using_AiiDA_at_PGI#Circumventing_SSH_open_and_close_limits_of_firewalls_by_ssh_tunnels
.. _official guide: https://www.flapw.de/site/Install/

To use AiiDA, it has to be installed on your local machine and configured properly. The detailed
description of all required steps can be found in the `AiiDA`_ documentation.
However, a small guide presented
below (which basically duplicates more detailed instructions given in `AiiDA`_) shows an example of
installation of AiiDA-FLEUR.

Installation of python packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
First of all, make sure that you have all required libraries that are `needed`_ for AiiDA.

.. note::

    If you use a cooperative machine, you might need to contact to your IT department to help you
    with setting up some libraries such as postgres and RabbitMQ.


In order to safely install AiiDA, you need to set up a virtual environment which protects you local
settings and packages.

Currently, AiiDA-FLEUR supports both python 2 and python 3 environments. However, I recommended
using python 3 because python 2 will not be supported since 2020.
To set up a python 3 environment, run a command:

.. code-block:: bash

    python3 -m venv ~/.virtualenvs/aiidapy

This will create a directory in your home directory named ``.virtualenvs/aiidapy`` where all the
required packages will be installed. First, the virtual environment has to be activated via:

.. code-block:: bash

    source ~/.virtualenvs/aiidapy/bin/activate

After activation, your prompt should have ``(aiidapy)`` in front of it, indicating that you are
working inside the virtual environment.
To install the latest versions of AiiDA and AiiDA-FLEUR, you can create a folder
where source codes will be located. To do this, run:

.. code-block:: bash

    (aiidapy)$ mkdir <your_directory_AiiDA>
    (aiidapy)$ cd <your_directory_AiiDA>
    (aiidapy)$ git clone https://github.com/aiidateam/aiida-core.git
    (aiidapy)$ pip install -e .

Which will install aiida_core. Note ``-e`` option in the last line: it allows one to fetch updates
from GitHub without package reinstallation. AiiDA-FLEUR can be installed the same way:

.. code-block:: bash

    (aiidapy)$ mkdir <your_directory_FLEUR>
    (aiidapy)$ cd <your_directory_FLEUR>
    (aiidapy)$ git clone https://github.com/JuDFTteam/aiida-fleur.git
    (aiidapy)$ git checkout develop
    (aiidapy)$ pip install -e .

.. note::
        You may need to install additional packages that are not strongly required for aiida-core
        and aiida-fleur and will not be installed automatically with them:

        .. code-block:: bash

            (aiidapy)$ pip install <missing_package>

        For instance, after successful installation I did not manage to run a calculation because of
        missing `pymatgen` package. The problem was solved by simply running:

        .. code-block:: bash

            (aiidapy)$ pip install pymatgen


Installation test
^^^^^^^^^^^^^^^^^

To test if the aiida-fleur installation was successful use:

.. code-block:: bash

    (aiidapy)$ verdi plugin list aiida.calculations

Example output containing FLEUR calculations:

.. code-block:: shell

    * arithmetic.add
    * fleur.fleur
    * fleur.inpgen
    * templatereplacer

You can pass as a further parameter one (or more) plugin names to get more details on a given
plugin.

After you have installed AiiDA-FLEUR it is always a good idea to run
the automated standard test set once to check on the installation.
(for this make sure that postgres 'pg_ctl' command is in your path)

.. code-block:: shell

  cd aiida_fleur/tests/
  ./run_all_cov.sh


the output should look something like this

.. code-block:: shell

    (env_aiida)% ./run_all.sh
    ======================================= test session starts ================================
    platform darwin -- Python 2.7.15, pytest-3.5.1, py-1.5.3, pluggy-0.6.0
    rootdir: /home/github/aiida-fleur, inifile: pytest.ini
    plugins: cov-2.5.1
    collected 166 items                                                                                                                                                                                          
    
    test_entrypoints.py ............                                                      [  7%]
    data/test_fleurinp.py ................................................................[ 63%]
    parsers/test_fleur_parser.py ........                                                 [ 68%]
    tools/test_common_aiida.py .                                                          [ 68%]
    tools/test_common_fleur_wf.py ..                                                      [ 69%]
    tools/test_common_fleur_wf_util.py ..........                                         [ 75%]
    tools/test_element_econfig_list.py .......                                            [ 80%]
    tools/test_extract_corelevels.py ...                                                  [ 81%]
    tools/test_io_routines.py ..                                                          [ 83%]
    tools/test_parameterdata_util.py ..                                                   [ 84%]
    tools/test_read_cif_folder.py .                                                       [ 84%]
    tools/test_xml_util.py ................                                               [ 94%]
    workflows/test_workflows_builder_init.py .........                                    [100%]

    + coverage report

    ==================================== 166 passed in 22.53 seconds ===========================


If anything (especially a lot of tests) fails it is very likely that your
installation is messed up. Maybe some packages are missing (reinstall them by hand and report please).
The other problem could be that the AiiDA-FLEUR version you have installed is not compatible
with the aiida-core version you are running, since not all aiida-core versions are back-compatible.
We try to not break back compatibility within aiida-fleur itself.
Therefore, newer versions of it should still work with older versions of the FLEUR code,
but newer FLEUR releases force you to migrate to a newer aiida-fleur version.

AiiDA setup
----------------
Once AiiDA-FLEUR is installed, it it necessary to setup a profile, computers and
codes.

Profile setup
^^^^^^^^^^^^^
First, to set up a profile with a database, use:

.. code-block:: bash

    (aiidapy)$ verdi quicksetup

You will be asked to specify some information required to identify data generated by you. If this
command does not work for you, please set up a profile with a database manually following
instructions from the AiiDA `tutorial`_.

Before setting up a computer, run:

.. code-block:: bash

    (aiidapy)$ verdi daemon start
    (aiidapy)$ verdi status

The first line launches a daemon which is needed for AiiDA to work. The second one makes an
automated check if all necessary components are working. If all of your checks passed and you see
something like

.. code-block:: bash

    ✓ profile:     On profile quicksetup
    ✓ repository:  /Users/tsep/.aiida/repository/quicksetup
    ✓ postgres:    Connected to aiida_qs_tsep_060f34d14612eee921b9ec5433b36abf@None:None
    ✓ rabbitmq:    Connected to amqp://127.0.0.1?heartbeat=600
    ✓ daemon:      Daemon is running as PID 8369 since 2019-07-12 09:56:31

your AiiDA is set up properly and you can continue with next section.

Computers setup
^^^^^^^^^^^^^^^^^
Aiida needs to know how to access the computer on which you want to perform calculations. For this
you need to setup a computer instance (node) in the database. It can be done by:

.. code-block:: bash

    (aiidapy)$ verdi computer setup

An example of the input:

.. code-block:: bash

    Computer label: my_laptop
    Hostname: localhost
    Description []: This is my laptop.
    Transport plugin: local
    Scheduler plugin: direct
    Shebang line (first line of each script, starting with #!) [#!/bin/bash]:
    Work directory on the computer [/scratch/{username}/aiida/]: /Users/I/home/workaiida
    Mpirun command [mpirun -np {tot_num_mpiprocs}]:
    Default number of CPUs per machine: 1

after that, a vim editor pops out, where you need to specify prepend and append text where you can
specify required imports for you system. You can skip add nothing there if you need no additional
imports.

If you want to use a remote
machine via ssh, you need to specify this machine in ``~/.ssh/config/``:

.. code-block:: bash

    Host super_machine
      HostName super_machine.institute.de
      User user_1
      IdentityFile ~/.ssh/id_rsa
      Port 22
      ServerAliveInterval 60

and then use:

.. code-block:: bash

    Computer label: remote_cluster
    Hostname: super_machine
    Description []: This is a super_machine cluster.
    Transport plugin: ssh
    Scheduler plugin: slurm
    Shebang line (first line of each script, starting with #!) [#!/bin/bash]:
    Work directory on the computer [/scratch/{username}/aiida/]: /scratch/user_1/workaiida
    Mpirun command [mpirun -np {tot_num_mpiprocs}]: srun
    Default number of CPUs per machine: 24

.. note::

    `Work directory on the computer` is the place where all computational files will be stored.
    Thus, if you have a faster partition on your machine, I recommend you to use this partition.

The last step is to configure the computer via:

.. code-block:: bash

    verdi computer configure ssh remote_cluster

for ssh connections and

.. code-block:: bash

    verdi computer configure local remote_cluster

for local machines.

If you are using aiida-fleur inside FZ Jülich, you can find additional helpful instructions on
setting up the connection to JURECA (or other machine) on `iffwiki`_.

FLEUR and inpgen setup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Aiida-FLEUR uses two codes: FLEUR itself and an input generator called inpgen. Thus, two codes have
to be set up independently.

input generator
~~~~~~~~~~~~~~~
I recommend running input generator on your local machine because it runs fast and one usually
spends
more time waiting for the input to be uploaded to the remote machine. You need to install inpgen
code to your laptop first which can be done following the `official guide`_.

After inpgen is successfully installed, it has to be configured by AiiDA. Run:

.. code-block:: bash

    (aiidapy)$ verdi code setup

and fill all the required forms. An example:

.. code-block:: bash

    Label: inpgen
    Description []: This is an input generator code for FLEUR
    Default calculation input plugin: fleur.inpgen
    Installed on target computer? [True]: True
    Computer: my_laptop
    Remote absolute path: /Users/User/Codes/inpgen

after that, a vim editor pops out and you need to specify prepend and append text where you can
add required imports and commands for you system. Particularly in my case, I need to
set proper library paths for inpgen to run. Hence my prepend text looks like:

.. code-block:: bash

    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/intel/mkl/lib:/usr/local/intel/compilers_and_libraries_2019.3.199/mac/compiler/lib/

Now inpgen code is ready to be used.

FLEUR code
~~~~~~~~~~

FLEUR code can be set up the same way as the input generator. However, there is an important note
that has to be mentioned.

.. note::
        If you use an HDF version of the FLEUR code then AiiDA-FLEUR plugin should know this. That
        is because names of generated output files vary between HDF and standard FLEUR versions.
        To properly set up an HDF version of the code, you *must* mention HDF5 (or hdf5) in the code
        description and not change it in the future. An example of setting up an HDF version:

        .. code-block:: bash

            Label: fleur
            Description []: This is the FLEUR code compiled with HDF5.
            Default calculation input plugin: fleur.fleur
            Installed on target computer? [True]: True
            Computer: remote_cluster
            Remote absolute path: /scratch/user/codes/fleur_MPI

