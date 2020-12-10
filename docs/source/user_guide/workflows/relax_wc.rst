.. _relax_wc:

Fleur structure optimization workchain
--------------------------------------

* **Current version**: 0.2.1
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

.. _exposed: https://aiida.readthedocs.io/projects/aiida-core/en/latest/working/workflows.html#working-workchains-expose-inputs-outputs

Input nodes
^^^^^^^^^^^

The FleurSSDispWorkChain employs
`exposed`_ feature of the AiiDA, thus inputs for the nested
:ref:`SCF<scf_wc>` workchain should be passed in the namespace
``scf``.

+-----------------+-----------------------------+---------------------------------+----------+
| name            | type                        | description                     | required |
+=================+=============================+=================================+==========+
| scf             | namespace                   | inputs for nested SCF WorkChain | yes      |
+-----------------+-----------------------------+---------------------------------+----------+
| final_scf       | namespace                   | inputs for a final SCF WorkChain| no       |
+-----------------+-----------------------------+---------------------------------+----------+
| wf_parameters   | :py:class:`~aiida.orm.Dict` | Settings of the workchain       | no       |
+-----------------+-----------------------------+---------------------------------+----------+


Workchain parameters and its defaults
.....................................

.. _FLEUR relaxation: https://www.flapw.de/site/xml-inp/#structure-relaxations-with-fleur

  * ``wf_parameters``: :py:class:`~aiida.orm.Dict` - Settings of the workflow behavior. All possible
    keys and their defaults are listed below:

    .. literalinclude:: code/relax_parameters.py


Output nodes
^^^^^^^^^^^^^

  * ``output_relax_wc_para``: :py:class:`~aiida.orm.Dict` - Information of workflow results
  * ``optimized_structure``: :py:class:`~aiida.orm.StructureData` - Optimized structure

.. _layout_relax:

Layout
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Geometry optimization workchain always submits SCF WC using inputs given in the ``scf`` namespace.
Thus one can start with a structure, FleurinpData or converged/not-fully-converged charge density.

Output nodes
^^^^^^^^^^^^^^^^^^^

+-------------------------+------------------------------------------------------+------------------------------------------------------+
| name                    | type                                                 | comment                                              |
+=========================+======================================================+======================================================+
| output_relax_wc_para    | :py:class:`~aiida.orm.Dict`                          | results of the workchain                             |
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

+-----------+----------------------------------------------------------
| Code      | Meaning                                                 |
+-----------+---------------------------------------------------------+
| 230       | Input: Invalid workchain parameters given.              |
+-----------+---------------------------------------------------------+
| 231       | Input: Inpgen missing in input for final scf.           |
+-----------+----------------------------------------------------------
| 350       | The workchain execution did not lead to                 |
|           | relaxation criterion. Thrown in the very                |
|           | end of the workchain.                                   |
+-----------+---------------------------------------------------------+
| 351       | SCF Workchains failed for some reason.                  |
+-----------+---------------------------------------------------------+
| 352       | Found no relaxed structure info in the output of SCF    |
+-----------+---------------------------------------------------------+
| 353       | Found no SCF output                                     |
+-----------+---------------------------------------------------------+
| 354       | Force is small, switch to BFGS                          |
+-----------+---------------------------------------------------------+

Exit codes duplicating FleurCalculation exit codes:

+-----------+------------------------------------------------------------------------------+
| Exit code | Reason                                                                       |
+===========+==============================================================================+
| 311       | FLEUR calculation failed because atoms spilled to the vacuum                 |
+-----------+------------------------------------------------------------------------------+
| 313       | Overlapping MT-spheres during relaxation                                     |
+-----------+------------------------------------------------------------------------------+

Example usage
^^^^^^^^^^^^^

.. literalinclude:: code/relax_submission.py
