Getting started
===============

Installation of AiiDA-FLEUR
+++++++++++++++++++++++++++

.. _downloading: https://github.com/JuDFTteam/aiida-fleur
.. _AiiDA: https://aiida.readthedocs.io/projects/aiida-core/en/latest/
.. _tutorial: https://aiida.readthedocs.io/projects/aiida-core/en/latest/install/installation.html#aiida-profile-setup
.. _needed: https://aiida.readthedocs.io/projects/aiida-core/en/latest/install/prerequisites.html
.. _iffwiki: https://iffwiki.fz-juelich.de/Using_AiiDA_at_PGI#Circumventing_SSH_open_and_close_limits_of_firewalls_by_ssh_tunnels
.. _official guide: https://www.flapw.de/MaX-4.0/documentation/installation/

To use AiiDA, it has to be installed on your local machine and configured properly. The detailed
description of all required steps can be found in the `AiiDA`_ documentation.
However, a small guide presented below shows an example of installation of AiiDA-FLEUR.

Installation of python packages
-------------------------------

First of all, make sure that you have all required libraries that are `needed`_ for AiiDA.

.. note::

    If you use a cooperative machine, you might need to contact to your IT department to help you
    with setting up some libraries such as postgres and RabbitMQ.

In order to safely install AiiDA, you need to set up a virtual environment to protect your local
settings and packages.
To set up a python3 environment, run:

.. code-block:: bash

    python3 -m venv ~/.virtualenvs/aiidapy

This will create a directory in your home directory named ``.virtualenvs/aiidapy`` where all the
required packages will be installed. Next, the virtual environment has to be activated:

.. code-block:: bash

    source ~/.virtualenvs/aiidapy/bin/activate

After activation, your prompt should have ``(aiidapy)`` in front of it, indicating that you are
working inside the virtual environment.

To install the latest official releases of AiiDA and AiiDA-FLEUR, run:

.. code-block:: bash

    (aiidapy)$ pip install aiida-fleur>=1.0

The command above will automatically install AiiDA itself as well since AiiDA-FLEUR has a
corresponding requirement.

If you want to work with the development version of AiiDA-FLEUR, you should consider installing
AiiDA and AiiDA-FLEUR from corresponding GitHub repositories. To do this, run:

.. code-block:: bash

    (aiidapy)$ mkdir <your_directory_AiiDA>
    (aiidapy)$ git clone https://github.com/aiidateam/aiida-core.git
    (aiidapy)$ cd aiida_core
    (aiidapy)$ pip install -e .

Which will install aiida_core. Note ``-e`` option in the last line: it allows one to fetch updates
from GitHub without package reinstallation. AiiDA-FLEUR can be installed the same way:

.. code-block:: bash

    (aiidapy)$ mkdir <your_directory_FLEUR>
    (aiidapy)$ git clone https://github.com/JuDFTteam/aiida-fleur.git
    (aiidapy)$ cd aiida-fleur
    (aiidapy)$ git checkout develop
    (aiidapy)$ pip install -e .



AiiDA setup
+++++++++++

Once AiiDA-FLEUR is installed, it it necessary to setup a profile, computers and
codes.

Profile setup
-------------

First, to set up a profile with a database, use:

.. code-block:: bash

    (aiidapy)$ verdi quicksetup

You will be asked to specify information required to identify data generated by you. If this
command does not work for you, please set up a profile manually via `verdi setup` following
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
---------------

AiiDA needs to know how to access the computer that you want to use for FLEUR calculations.
Therefore you need to set up a computer - this procedure will create a representation (node) of
computational computer in the database which will be used later. It can be done by:

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
    Thus, if you have a faster partition on your machine, I recommend you to use this one.

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
----------------------

AiiDA-FLEUR uses two codes: FLEUR itself and an input generator called inpgen. Thus, two codes have
to be set up independently.

Input generator
^^^^^^^^^^^^^^^

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
set proper library paths. Hence my prepend text looks like:

.. note::
    The default expected Input generator version is >=32 i.e >=MaX5.1. 
    If you want to install older version of the input generator you *must* specify a 'version' key 
    under the 'extras' of the code node i.e for example code.set_extra('version', 31). 

.. code-block:: bash

    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/intel/mkl/lib:/usr/local/intel/compilers_and_libraries_2019.3.199/mac/compiler/lib/

Now inpgen code is ready to be used.

FLEUR code
^^^^^^^^^^

FLEUR code can be set up the same way as the input generator. However, there is an important note
that has to be mentioned.

.. note::
        If you use an HDF version of the FLEUR code then AiiDA-FLEUR plugin should know this. The
        main reason for this is that names of output files vary between HDF and standard FLEUR versions.
        To properly set up an HDF version of the code, you *must* mention HDF5 (or hdf5) in the code
        description and not change it in the future. An example of setting up an HDF version:

        .. code-block:: bash

            Label: fleur
            Description []: This is the FLEUR code compiled with HDF5.
            Default calculation input plugin: fleur.fleur
            Installed on target computer? [True]: True
            Computer: remote_cluster
            Remote absolute path: /scratch/user/codes/fleur_MPI

Installation test
-----------------

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
the automated standard test set once to check on the installation
(make sure that postgres can be called via 'pg_ctl' command)

.. code-block:: shell

  cd aiida_fleur/tests/
  ./run_all_cov.sh


the output should look something like this

.. code-block:: shell

    (env_aiida)% ./run_all_cov.sh
    ================================== test session starts ===================================
    platform darwin -- Python 3.7.6, pytest-5.3.1, py-1.8.0, pluggy-0.12.0
    Matplotlib: 3.1.1
    Freetype: 2.6.1
    rootdir: /Users/tsep/Documents/aiida/aiida-fleur, inifile: pytest.ini
    plugins: mpl-0.10, cov-2.7.1
    collected 555 items

    test_entrypoints.py ...................                                            [  3%]
    data/test_fleurinp.py ............................................................ [ 14%]
    .......................................                                            [ 21%]
    data/test_fleurinpmodifier.py ..                                                   [ 21%]
    parsers/test_fleur_parser.py ........                                              [ 23%]
    tools/test_StructureData_util.py ...................                               [ 26%]
    tools/test_common_aiida.py .....                                                   [ 27%]
    tools/test_common_fleur_wf.py ...s..s.s.                                           [ 29%]
    tools/test_common_fleur_wf_util.py .....s.s....s.....s                             [ 32%]
    tools/test_data_handling.py .                                                      [ 32%]
    tools/test_dict_util.py ......                                                     [ 33%]
    tools/test_element_econfig_list.py .......                                         [ 35%]
    tools/test_extract_corelevels.py ...                                               [ 35%]
    tools/test_io_routines.py ..                                                       [ 36%]
    tools/test_read_cif_folder.py .                                                    [ 36%]
    tools/test_xml_util.py ..........s................................................ [ 46%]
    ....sss..ssss................s...............ss.......................sssssss..s.. [ 61%]
    .................sssssssssssssssssss.........sss........................s......... [ 76%]
    ...................s......................sss........................s............ [ 91%]
    ................s...............                                                   [ 96%]
    workflows/test_workflows_builder_init.py .................                         [100%]

    + coverage report

    ===================== 500 passed, 55 skipped, 21 warnings in 51.09s ======================


No worries about skipped tests - they appear due to technical implementation of tests and contain
some information for developers. For a user it is important to make sure that the others
do not fail: if anything (especially a lot of tests) fails it is very likely that your
installation is messed up. Some packages might be missing (reinstall them by hand and report
to development team). The other problem could be that the AiiDA-FLEUR version you have
installed is not compatible with the AiiDA version you are running, since not all
AiiDA versions are back-compatible.
