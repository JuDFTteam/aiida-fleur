.. _relax_wc:

Fleur structure optimization workchain
--------------------------------------

* **Current version**: 0.1.1
* **Class**: :py:class:`~aiida_fleur.workflows.relax.FleurRelaxWorkChain`
* **String to pass to the** :py:func:`~aiida.plugins.WorkflowFactory`: ``fleur.relax``
* **Workflow type**: Basic workflow
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

  * ``fleur``: :py:class:`~aiida.orm.Code` - Fleur code using the ``fleur.fleur`` plugin
  * ``inpgen``, optional: :py:class:`~aiida.orm.Code` - Inpgen code using the ``fleur.inpgen``
    plugin
  * ``wf_parameters``: :py:class:`~aiida.orm.Dict`, optional - Settings
    of the workflow behavior
  * ``structure``: :py:class:`~aiida.orm.StructureData`, optional: Crystal structure
    data node.
  * ``calc_parameters``: :py:class:`~aiida.orm.Dict`, optional -
    FLAPW parameters, used by inpgen
  * ``fleurinp``: :py:class:`~aiida_fleur.data.fleurinp.FleurinpData`, optional: Fleur input data
    object representing the fleur input files
  * ``remote_data``: :py:class:`~aiida.orm.RemoteData`, optional - The remote folder of
    the previous calculation
  * ``options``: :py:class:`~aiida.orm.Dict`, optional - AiiDA options
    (queues, cpus)
  * ``settings``: :py:class:`~aiida.orm.Dict`, optional - special settings

Returns nodes
^^^^^^^^^^^^^

  * ``out``: :py:class:`~aiida.orm.Dict` - Information of workflow results
  * ``optimized_structure``: :py:class:`~aiida.orm.StructureData` - Optimized structure

Default inputs
^^^^^^^^^^^^^^
Workflow parameters.

.. code-block:: python

    wf_parameters_dict = {'fleur_runmax': 4,       # needed for SCF
                   'alpha_mix': 0.015,             # Sets alpha mixing parameter
                   'relax_iter': 5,                # Maximum number of optimization iterations
                   'force_criterion': 0.001,       # Sets the threshold of the largest force
                   'force_converged' : 0.002,      # needed for SCF
                   'serial' : False,               # needed for SCF
                   'force_dict': {'qfix': 2,       # needed for SCF
                                  'forcealpha': 0.5,
                                  'forcemix': 'BFGS'},
                   'itmax_per_run' : 30,           # needed for SCF
                   'inpxml_changes' : [],          # needed for SCF
                   }

Supported input configurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Geometry optimization workchain has several
input combinations that implicitly define the workchain layout. Depending
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

Example usage
^^^^^^^^^^^^^
Has to be documented.

Output node example
^^^^^^^^^^^^^^^^^^^
For now output node contains the minimal amount of information. The content can be easily extended
on demand, please contact to developers for request.

.. code-block:: python

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

+------+-------------------------------+--------------------------------------------------------------------------------------------------------+
| Code | Name                          | Meaning                                                                                                |
+------+-------------------------------+--------------------------------------------------------------------------------------------------------+
| 230  | ERROR_INVALID_INPUT_RESOURCES | Input nodes do not correspond to any valid input configuration.                                        |
+------+-------------------------------+--------------------------------------------------------------------------------------------------------+
| 231  | ERROR_INVALID_CODE_PROVIDED   | Input codes do not correspond to fleur or inpgen codes respectively.                                   |
+------+-------------------------------+--------------------------------------------------------------------------------------------------------+
| 350  | ERROR_DID_NOT_CONVERGE        | The workchain execution did not lead to relaxation criterion. Thrown in the vary end of the workchain. |
+------+-------------------------------+--------------------------------------------------------------------------------------------------------+
| 351  | ERROR_RELAX_FAILED            | A relaxation iteration (a SCF workchain) failed.                                                       |
+------+-------------------------------+--------------------------------------------------------------------------------------------------------+
| 352  | ERROR_NO_RELAX_OUTPUT         | No parsed relax.xml output of SCF workchain found.                                                     |
+------+-------------------------------+--------------------------------------------------------------------------------------------------------+

If your workchain crashes and stops in *Excepted* state, please open a new issue on the Github page.
