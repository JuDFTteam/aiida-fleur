.. _relax_wc:

Fleur structure optimization workchain
--------------------------------------

* **Current version**: 0.1.1
* **Class**: :py:class:`~aiida_fleur.workflows.relax.FleurRelaxWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.relax``
* **Workflow type**: Technical
* **Aim**: Structure optimization of a given structure
* **Computational demand**: Several :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain`
* **Database footprint**: Output node with information, full provenance, ``~ 10+10*FLEUR Jobs`` nodes

.. contents::


Import Example:

.. code-block:: python

    from aiida_fleur.workflows.relax import FleurRelaxWorkChain
    #or
    WorkflowFactory('fleur.relax')

Description/Purpose
^^^^^^^^^^^^^^^^^^^
Optimizes the structure in a way the largest force is lower than a given threshold.

Uses :py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain` to converge forces first,
checks if the largest force is smaller than the
threshold. If the largest force is bigger, submits a new
:py:class:`~aiida_fleur.workflows.scf.FleurScfWorkChain` for next step structure
proposed by FLEUR.

All structure optimization routines implemented in the FLEUR code, the workchain only wraps it.

Input nodes
^^^^^^^^^^^

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
:ref:`layout_relax` section.

Workchain parameters and its defaults
.....................................

.. _FLEUR relaxation: https://www.flapw.de/site/xml-inp/#structure-relaxations-with-fleur

  * ``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
    keys and their defaults are listed below:

    .. literalinclude:: code/relax_parameters.py

    **'force_dict'** contains parameters that will be inserted into the ``inp.xml`` in case of
    force convergence mode. Usually this sub-dictionary does not affect the convergence, it affects
    only the generation of ``relax.xml`` file. Read more in `FLEUR relaxation`_ documentation.

    .. note::

      Only one of ``density_converged``, ``energy_converged`` or ``force_converged``
      is used by the workchain that corresponds to the **'mode'**. The other two are ignored.

  * ``options``: :py:class:`~aiida.orm.Dict` - AiiDA options (computational resources).
    Example:

    .. code-block:: python

         'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 1},
         'max_wallclock_seconds': 6*60*60,
         'queue_name': '',
         'custom_scheduler_commands': '',
         'import_sys_environment': False,
         'environment_variables': {}

Output nodes
^^^^^^^^^^^^^

  * ``out``: :py:class:`~aiida.orm.Dict` - Information of workflow results
  * ``optimized_structure``: :py:class:`~aiida.orm.StructureData` - Optimized structure

.. _layout_relax:

Supported input configurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Geometry optimization workchain has several
input combinations that implicitly define the input processing. Depending
on the setup of the inputs, one of four supported scenarios will happen:

1. **fleurinp**:

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation.

2. **fleurinp** + **parent_folder** (FLEUR):

      Files, belonging to the **fleurinp**, will be used as input for the first
      FLEUR calculation. Moreover, initial charge density will be
      copied from the folder of the parent calculation.

3. **parent_folder** (FLEUR):

      inp.xml file and initial
      charge density will be copied from the folder of the parent FLEUR calculation.

4. **structure**:

      inpgen code will be used to generate a new **fleurinp** using a given structure.

.. warning::

  One *must* keep one of the supported input configurations. In other case the workchain will
  stop throwing non-zero exit status or more seriously, will make unexpected actions.


Output nodes
^^^^^^^^^^^^^^^^^^^

+-------------------------+------------------------------------------------------+------------------------------------------------------+
| name                    | type                                                 | comment                                              |
+=========================+======================================================+======================================================+
| out                     | :py:class:`~aiida.orm.Dict`                          | results of the workchain                             |
+-------------------------+------------------------------------------------------+------------------------------------------------------+
| optimized_structure     | :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`  | FleurinpData that was used (after all modifications) |
+-------------------------+------------------------------------------------------+------------------------------------------------------+

For now output node contains the minimal amount of information. The content can be easily extended
on demand, please contact to developers for request.

.. code-block:: python

    # this is a content of out output node
    {
        "errors": [],
        "force": [
            0.03636428
        ],
        "force_iter_done": 1,
        "info": [],
        "initial_structure": "181c1e8d-3c56-4009-b0bb-e8b76cb417e2",
        "warnings": [],
        "workflow_name": "FleurRelaxWorkChain",
        "workflow_version": "0.1.0"
    }

Error handling
^^^^^^^^^^^^^^
A list of implemented exit codes:

+------+--------------------------------------------------------------------------------------------------------+
| Code | Meaning                                                                                                |
+------+--------------------------------------------------------------------------------------------------------+
| 230  | Input nodes do not correspond to any valid input configuration.                                        |
+------+--------------------------------------------------------------------------------------------------------+
| 231  | Input codes do not correspond to fleur or inpgen codes respectively.                                   |
+------+--------------------------------------------------------------------------------------------------------+
| 350  | The workchain execution did not lead to relaxation criterion. Thrown in the vary end of the workchain. |
+------+--------------------------------------------------------------------------------------------------------+
| 351  | A relaxation iteration (a SCF workchain) failed.                                                       |
+------+--------------------------------------------------------------------------------------------------------+
| 352  | No parsed relax.xml output of SCF workchain found.                                                     |
+------+--------------------------------------------------------------------------------------------------------+
| 354  | Found no fleurinpData in the last SCF workchain                                                        |
+------+--------------------------------------------------------------------------------------------------------+

If your workchain crashes and stops in *Excepted* state, please open a new issue on the Github page
and describe the details of the failure.

Example usage
^^^^^^^^^^^^^
Has to be documented.