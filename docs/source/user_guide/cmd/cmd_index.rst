The command line interface (CLI)
================================

Or how-to manually work or script from the terminal.

Besides the python API, aiida-fleur comes with a builtin command line interface (CLI) `aiida-fleur`,
which exposes functionalities of aiida-fleur on the command line, similar to the `verdi` commands of `aiida-core`. This interface is built using the `click` library and supports tab-completion. Of course everything you can do through the CLI and much more you can also do through the python API.

Here you will learn how to use this CLI. Everything in a code block with a "`$`" in front can be executed in a shell, if not otherwise indicated. Expected output is displayed below the command.
If a code block if a "`$`" contains "`<>`" it means that you have to replace it with what stands inside. For example `<scf-wc_pk>` means you have to type in the "`pk/id`" of the SCF workflow which was run.

General information
+++++++++++++++++++

To enable tab-completion, add the following to your shell loading script, e.g. the .bashrc or virtual environment activate script, or execute:

.. code-block:: bash

    eval "$(_AIIDA_FLEUR_COMPLETE=source aiida-fleur)"

In general, to learn about a command you can execute every command with the `-h/++help` option to see its help string. This will show you what the command does and what arguments, options and defaults it has. If it is a command group it will show you all sub-commands.

Example command group:

.. code-block:: bash

    $ aiida-fleur -h
    Usage: aiida-fleur [OPTIONS] COMMAND [ARGS]...
    
      CLI for the `aiida-fleur` plugin.
    
    Options:
      -p, ++profile PROFILE  Execute the command for this profile instead of the
                             default profile.
    
      -h, ++help             Show this message and exit.
    
    Commands:
      data      Commands to create and inspect data nodes.
      launch    Commands to launch workflows and calcjobs of aiida-fleur.
      plot      Invoke the plot_fleur command on given nodes
      workflow  Commands to inspect aiida-fleur workchains.

Example for a command:

.. code-block:: bash

    $ aiida-fleur launch scf -h
    Usage: aiida-fleur launch scf [OPTIONS]
    
      Launch a scf workchain
    
    Options:
      -s, ++structure STRUCTUREFILE   StructureData node, given by pk or uuid or
                                      file in any for mat which will be converted.
                                      [default: (dynamic)]
    
      -i, ++inpgen CODE               A code node or label for an inpgen
                                      executable.  [default: (dynamic)]
    
      -calc_p, ++calc-parameters DATA
                                      Dict with calculation (FLAPW) parameters to
                                      build, which will be given to inpgen.
    
      -set, ++settings DATA           Settings node for the calcjob.
      -inp, ++fleurinp DATA           FleurinpData node for the fleur calculation.
      -f, ++fleur CODE                A code node or label for a fleur executable.
                                      [default: (dynamic)]
    
      -wf, ++wf-parameters DATA       Dict containing parameters given to the
                                      workchain.
    
      -P, ++parent-folder DATA        The PK of a parent remote folder (for
                                      restarts).
    
      -d, ++daemon                    Submit the process to the daemon instead of
                                      running it locally.  [default: False]
    
      -set, ++settings DATA           Settings node for the calcjob.
      -opt, ++option-node DATA        Dict, an option node for the workchain.
      -h, ++help                      Show this message and exit.    
        
For the full automatic documentation of all commands checkout the :ref:`Commandline Interface (CLI) section <aiidafleur_cmdline>` in the module guide.

Overview of the main commands
+++++++++++++++++++++++++++++

The main commands groups of `aiida-fleur` are `data`, `launch`, `plot` and `workflow`.

The `data` group contains commands to create and inspect data nodes, for utility which is more specific to `aiida-fleur`and not covered by the `verdi data` commands of `aiida-core`. 
Sub-commands of `aiida-fleur data` include:

.. code-block:: bash

    fleurinp   Commands to handle `FleurinpData` nodes.
    parameter  Commands to create and inspect `Dict` nodes containing FLAPW parameters
    structure  Commands to create and inspect `StructureData` nodes.

The `launch` group contains commands to launch workflows/workchains and calcjobs of `aiida-fleur` from the shell. 
Sub-commands of `aiida-fleur launch` include:

.. code-block:: bash

    banddos          Launch a banddos workchain
    corehole         Launch a corehole workchain
    create_magnetic  Launch a create_magnetic workchain
    dmi              Launch a dmi workchain
    eos              Launch a eos workchain
    fleur            Launch a base_fleur workchain.
    init_cls         Launch an init_cls workchain
    inpgen           Launch an inpgen calcjob on given input If no code is...
    mae              Launch a mae workchain
    relax            Launch a base relax workchain # TODO final scf input
    scf              Launch a scf workchain
    ssdisp           Launch a ssdisp workchain

Important options out most launch commands include:
The `-S` option to provide a crystal structure. This can be either a `pk` or `uuid` from a `StructureData` node in the database or any file on disk in a format `ase` can read a structure from. This includes:


The `plot` command invokes the `plot_fleur` command of aiida fleur on given nodes. The `plot_fleur` command can visualize the output of a lot of aiida-fleur workchains.

The `workflow` command group has sub commands to inspect `aiida-fleur` workchains and prepare inputs.

.. code-block:: bash

    inputdict  Print data from Dict nodes input into any fleur process.
    res        Print data from Dict nodes returned or created by any fleur process



for example to launch an scf workchain on a given structure execute:

.. code-block:: bash

    $ aiida-fleur launch scf -i <inpgenpk> -f <fleurpk> -s <structurepk>

the command can also process structures in any format `ase` can handle, this includes `Cif`, `xsf` and `poscar` files. In such a case simply parse the path to the file:

.. code-block:: bash

    $ aiida-fleur launch scf -i <inpgenpk> -f <fleurpk> -s ./structure/Cu.cif

Confirm proper setup
++++++++++++++++++++

Quickly confirm that you have a computer and a code setup within your database.

.. code-block:: bash

    $ verdi computer list -a
    $ verdi code list -a

should display some configured computer and codes like this (notice the "`*`"s)::

    Info: List of configured computers
    Info: Use 'verdi computer show COMPUTERNAME' to display more detailed information
    * localhost
    * iffslurm

    # (use 'verdi code show CODEID' to see the details)
    # List of configured codes:
    * pk 149 - fleur_MPI_MaXR5_AMD@iffslurm
    * pk 150 - inpgen_MaXR5_AMD@iffslurm
    * pk 151 - inpgen_MaXR5_th1@iffslurm
    * pk 148 - fleur_MPI_MaXR5_th1@iffslurm

Prepare options nodes
+++++++++++++++++++++

Usually, when submitting calculations or workchains to a computer you have to provide an `options` node
in which you specify the queue to submit to and what computational resources the scheduler should allocate.
If the default option node is enough, or if the options for the default queue stored in the 'extras' of a code node, you do not need to provide this node.

To submit simulations to the `th1` queue with one node and run with two mpi processes execute. 

.. code-block:: bash

    aiida-fleur data options create -q 'th1' -N 1 -M 2

To submit simulations to the `th1-2020-32` queue with one node and run with two mpi processes execute. 

.. code-block:: bash

    aiida-fleur data options create -q 'th1-2020-32' -N 1 -M 2

You should see some output this::

    Success: Created and stored Options node <290>  <99f79d2e-04aa-4aaf-9b5f-9eabad8142d8>
    {
    "max_wallclock_seconds": 1800,
    "queue_name": "th1-2020-32",
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 2
        }
    }

Remember these pks (further named `opt_th1_pk` and `opt_amd_pk`) we need them further for launching workchains.
To display the contents of any `aiida.orm.Dict` node you can execute `verdi data dict show <pk>`.

Launching Calculations and workchains
+++++++++++++++++++++++++++++++++++++

Executing inpgen
++++++++++++++++

First we run a simple inpgen calculation from the command line on a Si structure provided by some cif file.

.. code-block:: bash

    $ aiida-fleur launch inpgen -i inpgen_MaXR5_th1 -s Si.cif -q th1

The structure is provided via the `-s` option, which can either be an identifier of a `StructureData` node or any supported format by `ase.io` (see https://wiki.fysik.dtu.dk/ase/ase/io/io.html?highlight=formats)
Among many others this includes:

```
cif, poscar, xsf, xyz, concar, outcar, xtd, xsd
```
One should be cautious when dealing with film and magnetic structures, because one has to make sure that the setup is as fleur needs it, and that all the magnetic information is preserved. One could use this command to convert most formats to fleur input, or with `++dry-run` one can get an input file for the input generator without storing anything in the database.
Also the execution above will block the interpreter until the job is finished and you see the logged output.
If the job is finished look at output of the process with

.. code-block:: bash

    $ verdi calcjob show <inpgen_calc_pk>
    $ verdi process report <inpgen_calc_pk>

.. code-block:: bash

    $ verdi outputls <inpgen_calc_pk>

will show you all files retrieved and stored in the aiida_repository by aiida.

.. code-block:: bash

    $ verdi calcjob gotocomputer <inpgen_calc_pk>

you can go to the remote computer to the directory where the job was executed (execute there `exit` or `logout` to logout from the remote computer.).
To see print the inp.xml file or any other retrieved output file execute

.. code-block:: bash

    $ verdi cajcjob outputcat <inpgen_calc_pk>

to see the input file for the inpgen calculation execute: 

.. code-block:: bash

    $ verdi calcjob inputcat <inpgen_calc_pk>

Executing Fleur
+++++++++++++++

Launch fleur calculation works in the same way, per default the `base_fleur` workchain is launched, which has some basic error handlers for fleur calculations. On the resulting `FleurinpData` from the inpgen calculation above we now launch a fleur calculation.

.. code-block:: bash

    $ aiida-fleur launch fleur ++fleur fleur_MaXR5_th1 -inp <fleurinp_pk>

Executing higher workflows
++++++++++++++++++++++++++

The interface to launch other workflows is very similar to the interface and options of the base calculations.
This time for each command we execute we add the `-d` option to submit the workflow to the daemon, executing them in the background instead of blocking the interpreter.
You can launch directly workflows like this 

.. code-block:: bash

    $ aiida-fleur launch scf -d -s Si.cif -i inpgen_MaXR5_th1 ++fleur fleur_MaXR5_th1 -opt <opt_th1_pk>
    $ aiida-fleur launch relax -d -s Si.cif -i inpgen_MaXR5_th1 ++fleur fleur_MaXR5_th1 -opt <opt_th1_pk>

launch an equation of states in the background to a different queue as for the other workflows

.. code-block:: bash

    $ aiida-fleur launch eos -s Si.cif -i inpgen_MaXR5_th1 ++fleur fleur_MaXR5_AMD -opt <opt_amd_pk>


Check with 

.. code-block:: bash

    verdi process list -p1

what the status of the workflows is while they execute.
When they are finished we can visualize the results using the aiida-fleur plot command, which visualizes workchain results statically with matplotlib or interactive with bokeh.

.. code-block:: bash

    $ aiida-fleur plot <scf-wc_pk>
    $ aiida-fleur plot <eos_wc_pk>

To easily display inputs and result dictionaries of aiida-fleur workchains you can utilize the workflow sub-commands.

.. code-block:: bash

    $ aiida-fleur workflow inputcat <scf_wc_pk>
    $ aiida-fleur workflow res ++info <scf-wc_pk>


Congratulation, you finished the aiida-fleur command line tutorial!
Thanks you! If you have any feedback, suggestions, feature requests, contact a developer or write an issue in the aiida-fleur git repository: https://github.com/JuDFTteam/aiida-fleur .

# Further comments, where to go from here:

(DFT) code inter operability
++++++++++++++++++++++++++++

You can now run a kkr scf with this relaxed structure as inputs over the similar `aiida-kkr` CLI.
For example:
For this first look at the output from the fleur relax workflow above and identify the pk of the optimized output structure

.. code-block:: bash

    $ verdi node show <relax_wc_pk>

.. code-block:: bash
   
    $ aiida-kkr launch scf -S <optimized_structure_pk> ++kkr <kkr_code>++voro <voronoi_code>

For more on this checkout the aiida-kkr tutorials.

Common workflows
++++++++++++++++

There is also work going on for common workflow interfaces between DFT codes.
For this checkout the aiida-common-workflow repository (https://github.com/aiidateam/aiida-common-workflows).
This is per default installed with all codes on quantum mobile, not here on iffaiida.
These common workflows use protocols ('moderate', 'fast', 'precise'), which are code specific, but which allow to execute the same type of workflow on otherwise the same input for example to following lines would execute an equation of states workflow with different codes on quantum mobile (otherwise needs more inputs):

.. code-block:: bash

    aiida-common-workflows launch eos -S Fe -p moderate fleur
    aiida-common-workflows launch eos -S Fe -p fast quantum_espresso
    aiida-common-workflows launch eos -S Fe -p precise siesta
    aiida-common-workflows launch eos -S Fe cp2k

Other useful commandline interfaces:
 - ASE: (https://wiki.fysik.dtu.dk/ase/cmdline.html)

Commandline versus python work
++++++++++++++++++++++++++++++

Work on the commandline is rather interactive, if you do not write a bash script to execute the commands you may loose information on the execution and maybe how to find things, if you have not logged something. The same if true for working with ipython.
For testing and small projects the command line interface is really useful and fast.
For large projects we still suggest strongly to use the python interface, because there you have the full functionality of `aiida-fleur` making it easier to execute a sequence of workflows which depend on each other.
