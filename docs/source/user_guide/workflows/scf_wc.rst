.. _scf_wc:

Fleur self-consistency field workflow
-------------------------------------

* **Current version**: 0.4.0
* **Class**: :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.scf``
* **Workflow type**: Technical
* **Aim**: Manage FLEUR SCF convergence
* **Computational demand**: Corresponding to several ``FleurCalculation``
* **Database footprint**: Output node with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes
* **File repository footprint**: no addition to the ``CalcJob`` run

.. contents::

Import Example:

.. code-block:: python

    from aiida_fleur.workflows.scf import FleurScfWorkChain
    #or
    WorkflowFactory('fleur.scf')

Description/Purpose
^^^^^^^^^^^^^^^^^^^

Converges the charge *density*, the *total energy* or the *largest force* of a given structure,
or stops because the maximum allowed retries are reached.

The workchain is designed to converge only one parameter independently on other parameters
(*largest force* is an exception because FLEUR code first checks if density was converged).
Simultaneous convergence of two or three parameters is not implemented to simplify the
code logic and because one almost always interested in a particular parameter. Moreover,
it was shown that the total energy tend to converge faster than the charge density.

This workflow manages an inpgen calculation (if needed) and several Fleur calculations.
It is one of the most core workchains and often deployed as a sub-workflow.

.. .. note::
..     The FleurScfWorkChain by default determines the calculation resources required for the given system and
..     with what hybrid parallelisation to launch Fleur. The resources in the option node given are the maximum
..     resources the workflow is allowed to allocate for one simulation (job).
..     You can turn off this feature by setting ``determine_resources = False`` in the ``wf_parameters``.

Input nodes
^^^^^^^^^^^

The table below shows all the possible input nodes of the SCF workchain.

+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| name            | type                                               | description                             | required |
+=================+====================================================+=========================================+==========+
| fleur           | :py:class:`~aiida.orm.Code`                        | Fleur code                              | yes      |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| inpgen          | :py:class:`~aiida.orm.Code`                        | Inpgen code                             | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| wf_parameters   | :py:class:`~aiida.orm.Dict`                        | Settings of the workchain               | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| structure       | :py:class:`~aiida.orm.StructureData`               | Structure data node                     | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| calc_parameters | :py:class:`~aiida.orm.Dict`                        | inpgen :ref:`parameters<scf_wc_layout>` | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| fleurinp        | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`| :ref:`FLEUR input<fleurinp_data>`       | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| remote_data     | :py:class:`~aiida.orm.RemoteData`                  | Remote folder of another calculation    | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| options         | :py:class:`~aiida.orm.Dict`                        | AiiDA options (computational resources) | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+
| settings        | :py:class:`~aiida.orm.Dict`                        | Special :ref:`settings<fleurinp_data>`  |          |
|                 |                                                    | for Fleur calculation                   | no       |
+-----------------+----------------------------------------------------+-----------------------------------------+----------+

Only ``fleur`` input is required. However, it does not mean that it is enough to specify ``fleur``
only. One *must* keep one of the supported input configurations described in the
:ref:`scf_wc_layout` section.

Workchain parameters and its defaults
.....................................

.. _FLEUR relaxation: https://www.flapw.de/site/xml-inp/#structure-relaxations-with-fleur


  * ``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
    keys and their defaults are listed below:

    .. literalinclude:: code/scf_parameters.py

    **'force_dict'** contains parameters that will be inserted into the ``inp.xml`` in case of
    force convergence mode. Usually this sub-dictionary does not affect the convergence, it affects
    only the generation of ``relax.xml`` file. Read more in `FLEUR relaxation`_ documentation.

    .. note::

      Only one of ``density_converged``, ``energy_converged`` or ``force_converged``
      is used by the workchain that corresponds to the **'mode'**. The other two are ignored.
      Exception: force mode uses both ``density_converged`` and ``force_converged`` because FLEUR
      code always converges density before forces.

  * ``options``: :py:class:`~aiida.orm.Dict` - AiiDA options (computational resources).
    Also see :ref:`fleur_parallelization` section.
    Example:

    .. code-block:: python

         'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
         'max_wallclock_seconds': 6*60*60,
         'queue_name': '',
         'custom_scheduler_commands': '',
         'import_sys_environment': False,
         'environment_variables': {}

Returns nodes
^^^^^^^^^^^^^

The table below shows all the possible output nodes of the SCF workchain.

+--------------------+-----------------------------------------------------+--------------------------------------------------------------------------+
| name               | type                                                | comment                                                                  |
+====================+=====================================================+==========================================================================+
| output_scf_wc_para | :py:class:`~aiida.orm.Dict`                         | results of the workchain                                                 |
+--------------------+-----------------------------------------------------+--------------------------------------------------------------------------+
| fleurinp           | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` | FleurinpData that was used (after all modifications)                     |
+--------------------+-----------------------------------------------------+--------------------------------------------------------------------------+
| last_calc          | Namespace                                           | Link to all output nodes (out dict, retrieved) of last Fleur calculation |
+--------------------+-----------------------------------------------------+--------------------------------------------------------------------------+

More details:

  * ``fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` - A
    :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` that was
    actually used for last :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain`.
    It usually differs from the input :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`
    because there are some hard-coded modifications in the SCF workchain.
  * ``last_calc``: namespace - A link to the output nodes
    of the last Fleur calculation. This includes the retrieved files, remote folder and output dictionary
  * ``output_scf_wc_para``: :py:class:`~aiida.orm.Dict` -  Main results of the workchain. Contains
    errors, warnings, convergence history and other information. An example:

    .. literalinclude:: code/scf_wc_outputnode.py

.. _scf_wc_layout:

Layout
^^^^^^
Similarly to :py:class:`~aiida_fleur.calculation.fleur.FleurCalculation`, SCF workchain has several
input combinations that implicitly define the behaviour of the workchain during
inputs processing. Depending
on the setup of the inputs, one of the four supported scenarios will happen:


1. **fleurinp** + **remote_data** (FLEUR):

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Moreover, initial charge density will be
      copied from the folder of the remote folder.

2. **fleurinp**:

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation.

3. **structure** + **inpgen** + *calc_parameters*:

      inpgen code and optional *calc_parameters* will be used to generate a
      new :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` using a given **structure**.
      Generated :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` will
      be used as an input for the first FLEUR calculation.

4. **structure** + **inpgen** + *calc_parameters* + **remote_data** (FLEUR):

      inpgen code and optional *calc_parameters* will be used to generate a
      new :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` using a given **structure**.
      Generated :py:class:`~aiida_fleur.data.fleurinp.FleurinpData` will
      be used as an input for the first FLEUR calculation. Initial charge density will be taken from given
      **remote_data** (FLEUR). **Note**: make sure that **remote_data** (FLEUR) corresponds to the same structure.

5. **remote_data** (FLEUR):

      inp.xml file and initial
      charge density will be copied from the remote folder.

For example, if you want to continue converging charge density, use the option 3.
If you want to change
something in the inp.xml and use old charge density you should use option 2. To do this, you can
retrieve a FleurinpData produced by the parent calculation and change it via FleurinpModifier,
use it as an input together with the RemoteFolder.

.. warning::

  One *must* keep one of the supported input configurations. In other case the workchain will
  stop throwing exit code 230.

The general layout does not depend on the scenario, SCF workchain sequentially submits several
FLEUR calculation to achieve a convergence criterion.

  .. figure:: /images/Workchain_charts_scf_wc.png
    :width: 50 %
    :align: center

Error handling
^^^^^^^^^^^^^^
In case of failure the SCF WorkChain should throw one of the :ref:`exit codes<exit_codes>`:

+-----------+---------------------------------------------+
| Exit code | Reason                                      |
+===========+=============================================+
| 230       | Invalid input, please                       |
|           | check input configuration                   |
+-----------+---------------------------------------------+
| 231       | Invalid code node specified, check inpgen   |
|           | and fleur code nodes                        |
+-----------+---------------------------------------------+
| 232       | Input file modification failed              |
+-----------+---------------------------------------------+
| 233       |Input file was corrupted after  modifications|
+-----------+---------------------------------------------+
| 360       | Inpgen calculation failed                   |
+-----------+---------------------------------------------+
| 361       | Fleur calculation failed                    |
+-----------+---------------------------------------------+
| 362       | SCF cycle did not lead to convergence,      |
|           | maximum number of iterations exceeded       |
+-----------+---------------------------------------------+

If your workchain crashes and stops in *Excepted* state, please open a new issue on the Github page
and describe the details of the failure.

Plot_fleur visualization
^^^^^^^^^^^^^^^^^^^^^^^^
  Single node

  .. code-block:: python

    from aiida_fleur.tools.plot import plot_fleur

    plot_fleur(50816)

  .. figure:: /images/plot_fleur_scf1.png
    :width: 60 %
    :align: center

  .. figure:: /images/plot_fleur_scf2.png
    :width: 60 %
    :align: center

  Multi node

  .. code-block:: python

    from aiida_fleur.tools.plot import plot_fleur

    plot_fleur(scf_pk_list)

  .. figure:: /images/plot_fleur_scf_m1.png
    :width: 60 %
    :align: center

  .. figure:: /images/plot_fleur_scf_m2.png
    :width: 60 %
    :align: center

Database Node graph
^^^^^^^^^^^^^^^^^^^
  .. code-block:: python

    from aiida_fleur.tools.graph_fleur import draw_graph

    draw_graph(50816)

  .. figure:: /images/scf_50816.pdf
    :width: 100 %
    :align: center

Example usage
^^^^^^^^^^^^^
  .. literalinclude:: code/scf_wc_submission.py
